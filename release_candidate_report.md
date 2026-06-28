# SolidWorks AI Studio v0.9.5 RC Acceptance Report

Generated from current v0.9.5 RC freeze evidence.

## Verdict

SolidWorks AI Studio = RC PASS

The RC candidate is frozen at `v0.9.5-rc.1`. The release candidate does not add AI Capability entries, Recipe entries, SolidWorks modules, low-level API navigation, Workbench architecture changes, or geometry-path changes.

## Version Line

| Component | Version |
|---|---:|
| Root package | `0.9.5-rc.1` |
| Desktop package | `0.9.5-rc.1` |
| Backend API | `0.9.5-rc.1` |
| Branch | `codex/v0.9.5-release-candidate-freeze` |
| Base commit before RC freeze changes | `393b89a20c083c15c616317fa9486ac3f32de671` |

## Release Artifacts

| Artifact | Bytes | SHA256 |
|---|---:|---|
| `dist/SolidWorks AI Studio Setup.exe` | 132,941,740 | `d36f9a4d9118615db99ec4719a3e93124c98a2788a2f1f704e465facde44c08f` |
| `dist/SolidWorks AI Studio Portable.exe` | 132,719,937 | `9edc074eaa5db01df399ba0a0451ddda18f4aca8cb23898a6bf849738c3ac704` |
| `dist/SolidWorks AI Studio Setup.exe.blockmap` | 139,878 | `b17bafd5abe26134f8b83120667a2437063269a96990b28a32846408b778c7ca` |
| `dist/win-unpacked/SolidWorks AI Studio.exe` | 232,351,232 | `e28e34ab6bec280d41dcf02910c4f3aea2d8c1fa9382f5c288aa0601d4c3fe01` |

## Current Real Evidence

| Area | Result |
|---|---:|
| Packaged E2E | `ok=true` |
| Text model | `glm-5.1`, `chat_verified=true` |
| Vision model | `doubao-seed-2.0-pro`, `vision_verified=true` |
| Visual validation | `visual_ok=true`, `degraded=false`, `vision_analysis_count=8`, `vision_error_count=0` |
| SolidWorks preflight | `can_run_real_com=true`, revision `33.5.0` |
| Natural-language run | `744ada29452d41c89f147efd9376edb5`, `stage=done`, `real_execution_verified=true` |
| Workbench task | `a101d773c84141cbbcbc7521a81faabb`, visible in Task History API/UI |
| Geometry evidence | `hole_features_restored=true`, `geometry_parity_verified=true` |
| Packaged page screenshots | Dashboard, Settings, AI CAD Studio / Capability Workbench, Task History, Integration, Developer |

## Install And First Start

The NSIS setup artifact was installed silently into a temporary validation directory, then started with a fresh user-data directory.

| Gate | Result |
|---|---:|
| Setup exit code | `0` |
| Installed EXE exists | `true` |
| First start rendered Dashboard | `true` |
| Local backend health | `ok=true`, version `0.9.5-rc.1` |
| Fresh config contains no API key | `true` |
| Screenshot non-blank | `true` |

## Evidence Package

Redacted evidence lives under:

```text
release_evidence/v0.9.5-rc.1/
```

The generated full evidence package lives under ignored outputs:

```text
outputs/v095_rc/latest/evidence_package/
```

Large binaries, CAD outputs, screenshots, Electron user-data caches, and local API keys are not committed.

## Known Limits

- `MCP solidworks_review_active` can still produce manual-preview warnings; RC acceptance uses packaged visual validation plus Workbench real evidence.
- A low-severity esbuild development-server advisory remains in `npm audit`; `npm audit --audit-level=high` passes.
- The RC evidence package records the base commit present when evidence was generated. The final Git commit that contains this report is reported separately after commit creation.
