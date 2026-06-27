# Release Checklist

## Repository Hygiene

- [ ] Generated directories are absent from source: `.venv`, `node_modules`, `dist`, `outputs`, `__pycache__`, `.pytest_cache`, `test-results`.
- [ ] `.gitignore` excludes generated and local-only files.
- [ ] No API keys, tokens, local private config, or large generated artifacts are staged.

## Verification

- [ ] `scripts/bootstrap.ps1`
- [ ] `python -m pytest backend/tests -q`
- [ ] `npm run typecheck --workspace apps/desktop`
- [ ] `npm test --workspace apps/desktop`
- [ ] `npm run smoke --workspace apps/desktop`
- [ ] `npm audit --audit-level=high`
- [ ] `scripts/build_backend.ps1`
- [ ] `scripts/build_desktop.ps1`
- [ ] `node scripts/v094_e2e_usable_app_validation.mjs` with `SWAI_VALIDATION_API_KEY`, `SWAI_VALIDATION_MODEL`, and `SWAI_VALIDATION_VISION_MODEL` supplied from local environment or user config.

## SolidWorks Validation

- [ ] `scripts/sw2025_preflight.ps1`
- [ ] `scripts/validate_error_scenarios.ps1`
- [ ] `scripts/solidworks_long_stability_mounting_plate.ps1 -Count 20`
- [ ] No Mock/Demo evidence is counted as real SolidWorks execution.

## Release Notes

- [ ] `CHANGELOG.md` updated.
- [ ] `RELEASE_NOTES_v0.9.0.md` updated.
- [ ] `VALIDATION_SUMMARY.md` updated with real evidence and limitations.

## v0.9.4 Evidence

- [ ] Packaged app starts from `dist/win-unpacked/SolidWorks AI Studio.exe`.
- [ ] Text model is verified through a real provider chat response.
- [ ] Vision model is verified through a real provider vision response.
- [ ] Dashboard, Settings, AI CAD Studio / Capability Workbench, Task History, Integration, and Developer screenshots are non-blank and assertion-checked.
- [ ] Natural language workflow reaches `stage=done` with `real_execution_verified=true`.
- [ ] Workbench `mounting_plate` reaches `real_execution_verified=true`, `hole_features_restored=true`, and `geometry_parity_verified=true`.
- [ ] Task History shows the current Workbench task ID.
- [ ] Visual validation reports `visual_ok=true` and `degraded=false`.
