# SolidWorks AI Studio v0.9.5-rc.2 Release Notes

v0.9.5-rc.2 is the local installation acceptance candidate. It takes the already frozen v0.9.5-rc.1 application and proves that the Windows installer and EXE package can be used locally through install, first start, real model validation, SolidWorks validation, functional execution, stability, error scenarios, diagnostics, uninstall, and reinstall.

## Scope

- No new AI Capability.
- No new Recipe.
- No new SolidWorks module.
- No new low-level API main navigation entry.
- No Workbench architecture refactor.
- No change to the verified `mounting_plate` geometry path.

## Deliverables

- `dist/SolidWorks AI Studio Setup.exe`
- `dist/SolidWorks AI Studio Portable.exe`
- `outputs/v095_rc2/latest/SolidWorks-AI-Studio-v0.9.5-rc.2-windows-x64.zip`
- `outputs/v095_rc2/latest/SolidWorks-AI-Studio-v0.9.5-rc.2-diagnostics.zip`
- `release_evidence/v0.9.5-rc.2/`

## Acceptance Gates

- Installed app launches from a real NSIS installation.
- Fresh user-data first start has no preloaded API key.
- `glm-5.1` text model returns a real chat response.
- `doubao-seed-2.0-pro` vision model returns a real vision response.
- SolidWorks COM preflight is ready.
- Natural-language CAD execution completes with real evidence.
- Workbench `mounting_plate` completes with real artifacts and four-hole geometry parity.
- Installed-app stability runs complete without failure.
- Error scenarios produce an explicit pass or non-destructive skipped-with-reason report.
- Diagnostics package is generated and redacted.
- Installer uninstall and reinstall both pass.

## Known Limits

- Error scenarios that would destructively alter the user's SolidWorks session or template configuration are reported as `skipped_with_reason` rather than forced.
- Large generated artifacts and local diagnostic zips are not committed; only redacted summaries and SHA256 hashes are committed.
