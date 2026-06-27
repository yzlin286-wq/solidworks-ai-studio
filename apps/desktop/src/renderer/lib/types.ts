export type StatusLevel = "pass" | "warn" | "fail" | "info";
export type RunStage = "queued" | "planning" | "generated" | "waiting_approval" | "running" | "reviewing" | "done" | "failed";
export type ViewKey = "dashboard" | "capabilities" | "tasks" | "integration" | "developer" | "settings";
export type CapabilityExecutionKind = "python_script" | "mcp_tool" | "prompt_context" | "documentation_only";
export type AddinRequirement = "none" | "motion" | "simulation" | "sheet_metal" | "weldments" | "other";
export type RealValidationStatus = "untested" | "passed" | "failed" | "skipped_with_reason";

export interface HealthResponse {
  ok: boolean;
  app: string;
  version: string;
  mode: "api";
  project_root: string;
  user_data_dir: string;
  time: string;
}

export interface LLMProfile {
  id: string;
  name: string;
  api_base_url: string;
  api_key: string;
  model: string;
  temperature: number;
  max_tokens: number;
  timeout_seconds: number;
}

export interface AppConfig {
  profiles: LLMProfile[];
  active_profile_id: string;
  theme: "dark" | "light" | "system";
  solidworks_skill_path: string;
  taste_skill_path: string;
  output_dir: string;
  validation_output_dir: string;
  part_template_path: string;
  assembly_template_path: string;
  drawing_template_path: string;
  require_approval: boolean;
  mock_mode: boolean;
}

export interface ConfigResponse {
  config: AppConfig;
  config_path: string;
  secure_storage: "config-file";
  note: string;
}

export interface PreflightCheck {
  key: string;
  label: string;
  status: StatusLevel;
  message: string;
  suggestion: string;
}

export interface PreflightResponse {
  mode: "solidworks" | "mock";
  checks: PreflightCheck[];
  can_run_real_com: boolean;
  solidworks_version: string;
  report_json: string;
  report_markdown: string;
  state?: string;
  stale?: boolean;
  started_at?: string | null;
  finished_at?: string | null;
  elapsed_seconds?: number | null;
}

export interface Capability {
  id: string;
  title: string;
  source_type: "skill_md" | "script" | "mcp_tool" | "reference" | "subskill" | "example";
  source_path: string;
  callable: boolean;
  execution_kind: CapabilityExecutionKind;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  requires_solidworks: boolean;
  requires_active_document: boolean;
  requires_part: boolean;
  requires_assembly: boolean;
  requires_drawing: boolean;
  requires_addin: AddinRequirement;
  ui_exposed: boolean;
  api_endpoint: string;
  test_case: string;
  real_sw2025_status: RealValidationStatus;
  skip_reason: string;
}

export interface CapabilityListResponse {
  generated_at: string;
  capabilities_path: string;
  capabilities: Capability[];
}

export interface SkillDocument {
  title: string;
  path: string;
  kind: "skill" | "reference" | "subskill" | "example" | "script" | "mcp" | "taste";
  modified_at: string | null;
  excerpt: string;
}

export interface SkillFunction {
  name: string;
  signature: string;
  module: string;
  doc: string;
}

export interface SkillIndexResponse {
  solidworks_available: boolean;
  taste_available: boolean;
  solidworks_path: string;
  taste_path: string;
  indexed_at: string;
  documents: SkillDocument[];
  functions: SkillFunction[];
  mcp_tools: string[];
  context_summary: string;
}

export interface AIPlanResponse {
  plan: string;
  risks: string[];
  required_files: string[];
  prompt: string;
  demo_mode: boolean;
  provider_verified_at?: string | null;
}

export interface GenerateScriptResponse {
  plan: string;
  risks: string[];
  required_files: string[];
  script: string;
  script_path: string;
  demo_mode: boolean;
  fallback_used?: boolean;
  fallback_reason?: string;
  provider_verified_at?: string | null;
}

export interface RunEvent {
  time: string;
  stage: RunStage;
  message: string;
  stdout: string;
  stderr: string;
}

export interface RunRecord {
  run_id: string;
  stage: RunStage;
  prompt: string;
  script_path: string;
  stdout: string;
  stderr: string;
  files: string[];
  events: RunEvent[];
  created_at: string;
  updated_at: string;
  real_execution_verified: boolean;
  evidence: Record<string, unknown>;
}

export interface SolidWorksExecutionRecord {
  run_id: string;
  capability_id: string;
  started_at: string | null;
  finished_at: string | null;
  status: "queued" | "running" | "passed" | "failed" | "cancelled" | "skipped";
  stdout: string;
  stderr: string;
  created_files: string[];
  active_document_before: string;
  active_document_after: string;
  error_summary: string;
  log_path: string;
  parameters: Record<string, unknown>;
  real_execution_verified: boolean;
  evidence: Record<string, unknown>;
  created_files_exist: boolean;
}

export interface SolidWorksActionResponse {
  ok: boolean;
  mode: "solidworks" | "mock";
  action: string;
  message: string;
  stdout: string;
  stderr: string;
  files: string[];
  data: Record<string, unknown>;
  real_execution_verified: boolean;
  evidence: Record<string, unknown>;
  active_document_before: string;
  active_document_after: string;
  created_files_exist: boolean;
}

export interface MCPStatusResponse {
  running: boolean;
  pid: number | null;
  command: string[];
  tools: string[];
  message: string;
}

export interface MCPConfigSnippetsResponse {
  snippets: Record<string, string>;
  server_path: string;
}

export interface RealTestRunResponse {
  ok: boolean;
  report_json: string;
  report_markdown: string;
  capability_matrix_csv: string;
  files_manifest_json: string;
  core_passed: number;
  core_failed: number;
  optional_skipped: Array<{
    capability_id: string;
    status: string;
    report_path: string;
    created_files: string[];
    skip_reason: string;
    error_summary: string;
  }>;
}

export interface TestConnectionResponse {
  ok: boolean;
  provider: string;
  message: string;
  latency_ms: number | null;
  models: string[];
  models_verified: boolean;
  chat_verified: boolean;
  provider_verified_at?: string | null;
}

export interface AICapability {
  id: string;
  title: string;
  group: string;
  status: string;
  maturity: string;
  ai_goal: string;
  user_intents: string[];
  execution_modes: string[];
  requires: string[];
  source_files: string[];
  default_outputs: string[];
  approval_required: boolean;
  source_missing: boolean;
  not_primary_entries: string[];
  recipes?: Recipe[];
}

export interface AICapabilityListResponse {
  generated_at: string;
  total: number;
  groups: Array<{ name: string; count: number; capability_ids: string[] }>;
  capabilities: AICapability[];
}

export interface Recipe {
  recipe_id: string;
  capability_id: string;
  title: string;
  description: string;
  parameters_schema: Record<string, unknown>;
  default_prompt: string;
  mock_artifacts: string[];
  maturity: string;
  real_execution: string;
}

export interface RecipeListResponse {
  generated_at: string;
  total: number;
  recipes: Recipe[];
}

export interface WorkbenchTask {
  task_id: string;
  capability_id: string;
  recipe_id: string;
  prompt: string;
  execution_mode: "mock" | "real";
  status: string;
  plan: Record<string, unknown>;
  script: string;
  validation: { ok?: boolean; issues?: string[]; warnings?: string[] };
  approved: boolean;
  artifacts: Array<{ name: string; path: string; exists: boolean; kind: string }>;
  evidence: Record<string, unknown>;
  error_summary: string;
  created_at: string;
  updated_at: string;
  real_execution_verified: boolean;
  mock_demo: boolean;
}

export interface WorkbenchTaskListResponse {
  total: number;
  tasks: WorkbenchTask[];
}
