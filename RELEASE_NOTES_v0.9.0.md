# SolidWorks AI Studio v0.9.0 Release Notes

v0.9.0 establishes SolidWorks AI Studio as an AI Capability Workbench rather than a raw SolidWorks API launcher.

## Highlights

- 27 AI capabilities organized by user-facing CAD workflow.
- 14 recipe entries with mock planning/execution and real-execution maturity tracking.
- 16 MCP tools surfaced for integration visibility.
- Approval-gated execution path retained for mutating SolidWorks operations.
- Real SolidWorks mounting-plate acceptance evidence captured with revision `33.5.0`.

## Validation Snapshot

- Backend pytest: 35 passed.
- Frontend Vitest: 7 passed.
- Playwright smoke: 1 passed.
- Packaged EXE runtime: `packaged_exe_ok=true`.
- LLM provider check: `llm_connection_ok=true`.
- Vision validation: `visual_ok=true`.
- Real task ID: `1aad1cc4590449d28c0ae15fb45c8d77`.

## Release Constraints

- This release does not add new SolidWorks low-level entry points.
- Mutating operations remain approval-gated.
- Mock/Demo execution is not accepted as real SolidWorks validation evidence.
