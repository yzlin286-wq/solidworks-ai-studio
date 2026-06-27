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

## SolidWorks Validation

- [ ] `scripts/sw2025_preflight.ps1`
- [ ] `scripts/validate_error_scenarios.ps1`
- [ ] `scripts/solidworks_long_stability_mounting_plate.ps1 -Count 20`
- [ ] No Mock/Demo evidence is counted as real SolidWorks execution.

## Release Notes

- [ ] `CHANGELOG.md` updated.
- [ ] `RELEASE_NOTES_v0.9.0.md` updated.
- [ ] `VALIDATION_SUMMARY.md` updated with real evidence and limitations.
