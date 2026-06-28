# Release Evidence

This directory stores small, redacted release evidence summaries that are safe to commit.

Current RC package:

```text
release_evidence/v0.9.5-rc.1/
```

Large generated artifacts are intentionally not committed:

- `dist/`
- `outputs/`
- CAD files and screenshots
- Electron user-data directories
- local API keys or provider configuration

Regenerate the current RC evidence package with:

```powershell
node scripts/create_v095_rc_evidence_package.mjs
```
