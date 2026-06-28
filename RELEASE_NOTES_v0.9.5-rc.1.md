# SolidWorks AI Studio v0.9.5-rc.1 Release Notes

v0.9.5-rc.1 is a release-candidate freeze of the already validated v0.9.4 end-to-end application. It does not add new AI capabilities, recipes, SolidWorks modules, Workbench architecture, or geometry behavior.

## What Is Frozen

- 27 AI Capability Registry entries.
- 14 Recipe Registry entries.
- Dashboard-first Workbench information architecture.
- Approval-gated task workflow: plan -> generate script -> static validation -> approval -> execute -> artifacts -> task history.
- `mounting_plate` four-corner-hole geometry parity.
- Real text model path through `glm-5.1`.
- Real vision model path through `doubao-seed-2.0-pro`.
- Packaged desktop build with custom icon and bundled FastAPI backend.

## Release Artifacts

- `dist/SolidWorks AI Studio Setup.exe`
- `dist/SolidWorks AI Studio Portable.exe`
- `dist/SolidWorks AI Studio Setup.exe.blockmap`
- `dist/win-unpacked/SolidWorks AI Studio.exe`

SHA256 hashes are recorded in:

```text
release_evidence/v0.9.5-rc.1/SHA256SUMS.txt
```

## Validation Snapshot

- Backend pytest: 37 passed.
- Frontend typecheck: passed.
- Vitest: 8 passed.
- Playwright smoke: 1 passed.
- npm audit high: passed.
- Secret scan: 0 hits.
- Packaged E2E: `ok=true`.
- Installer first start: `ok=true`.
- Text model: `glm-5.1`, `chat_verified=true`.
- Vision model: `doubao-seed-2.0-pro`, `vision_verified=true`.
- Visual validation: `visual_ok=true`, `degraded=false`.
- SolidWorks revision: `33.5.0`.
- Natural-language real run: `744ada29452d41c89f147efd9376edb5`.
- Workbench real task: `a101d773c84141cbbcbc7521a81faabb`.
- Geometry evidence: `hole_features_restored=true`, `geometry_parity_verified=true`.

## First-Start Notes

The installer was validated with a fresh user-data directory. The first launch rendered Dashboard, loaded local backend health with version `0.9.5-rc.1`, and confirmed the fresh config did not contain an API key.

Users must configure their own OpenAI-compatible API key in Settings. Keys are not included in release artifacts or evidence.

## Known Limits

- Mock workflows remain available only as explicit development/test evidence and are never counted as real SolidWorks validation.
- `MCP solidworks_review_active` may still require manual preview review; RC acceptance uses Workbench real evidence and visual-model validation.
- One low-severity esbuild development-server advisory may remain; high-level npm audit passes.
