# Release Checklist

## Repository Hygiene

- [ ] Generated directories are absent from source: `.venv`, `node_modules`, `dist`, `outputs`, `__pycache__`, `.pytest_cache`, `test-results`.
- [ ] `.gitignore` excludes generated and local-only files.
- [ ] No API keys, tokens, local private config, or large generated artifacts are staged.
- [ ] Version line is frozen at `0.9.5-rc.2` for root package, desktop package, and backend API.
- [ ] Release branch name reflects the RC line.

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
- [ ] `node scripts/v095_install_first_start_validation.mjs`
- [ ] `node scripts/create_v095_rc_evidence_package.mjs`
- [ ] `node scripts/v095_rc2_local_installation_acceptance.mjs`
- [ ] `node scripts/create_v095_rc2_delivery_evidence_package.mjs`
- [ ] `scripts/verify_clean_clone.ps1`

## SolidWorks Validation

- [ ] `scripts/sw2025_preflight.ps1`
- [ ] `scripts/validate_error_scenarios.ps1`
- [ ] `scripts/solidworks_long_stability_mounting_plate.ps1 -Count 20`
- [ ] No Mock/Demo evidence is counted as real SolidWorks execution.

## Release Notes

- [ ] `CHANGELOG.md` updated.
- [ ] `RELEASE_NOTES_v0.9.0.md` updated.
- [ ] `RELEASE_NOTES_v0.9.5-rc.1.md` updated.
- [ ] `RELEASE_NOTES_v0.9.5-rc.2.md` updated.
- [ ] `VALIDATION_SUMMARY.md` updated with real evidence and limitations.
- [ ] `release_candidate_report.md` says `RC PASS` only when current evidence proves every gate.
- [ ] `release_evidence/v0.9.5-rc.1/` contains redacted evidence and SHA256 hashes.
- [ ] `release_evidence/v0.9.5-rc.2/` contains redacted local-installation evidence and SHA256 hashes.

## v0.9.4 Evidence

- [ ] Packaged app starts from `dist/win-unpacked/SolidWorks AI Studio.exe`.
- [ ] Text model is verified through a real provider chat response.
- [ ] Vision model is verified through a real provider vision response.
- [ ] Dashboard, Settings, AI CAD Studio / Capability Workbench, Task History, Integration, and Developer screenshots are non-blank and assertion-checked.
- [ ] Natural language workflow reaches `stage=done` with `real_execution_verified=true`.
- [ ] Workbench `mounting_plate` reaches `real_execution_verified=true`, `hole_features_restored=true`, and `geometry_parity_verified=true`.
- [ ] Task History shows the current Workbench task ID.
- [ ] Visual validation reports `visual_ok=true` and `degraded=false`.

## v0.9.5 RC Freeze

- [ ] No AI Capability was added.
- [ ] No Recipe was added.
- [ ] No SolidWorks module or low-level user navigation entry was added.
- [ ] Existing Workbench information architecture is unchanged.
- [ ] `mounting_plate` geometry path is not modified except by prior verified parity work.
- [ ] Installer first start uses a fresh user-data directory and confirms no API key is preloaded.
- [ ] Release artifacts are recorded by SHA256 but not committed.
