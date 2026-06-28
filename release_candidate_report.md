# SolidWorks AI Studio v0.9.5-rc.2 Local Installation Acceptance Report

Generated from current v0.9.5-rc.2 local installation evidence.

## Verdict

SolidWorks AI Studio = RC2 LOCAL INSTALL PASS

The candidate is frozen at `v0.9.5-rc.2`. This release does not add AI Capability entries, Recipe entries, SolidWorks modules, low-level API navigation, Workbench architecture changes, or geometry-path changes.

## Version Line

| Component | Version |
|---|---:|
| Root package | `0.9.5-rc.2` |
| Desktop package | `0.9.5-rc.2` |
| Backend API | `0.9.5-rc.2` |
| Branch | `codex/v0.9.5-release-candidate-freeze` |
| Base commit before rc.2 changes | `905aa0197a919a8f89efb630b79c999049ceae43` |

## Local Installation Acceptance

| Gate | Result |
|---|---:|
| NSIS install | `install_ok=true` |
| First start | `first_start_ok=true` |
| Text model | `glm-5.1`, `chat_verified=true` |
| Vision model | `doubao-seed-2.0-pro`, `vision_verified=true` |
| SolidWorks COM | `solidworks_ready=true`, revision `33.5.0` |
| Natural-language real run | `7c15264f0de84b7a8b691c2d1bc5c941`, `real_execution_verified=true` |
| Workbench task | `676c9ecc96a142188c7435a3f4b1de26`, Task History API/UI visible |
| Geometry evidence | `hole_features_restored=true`, `geometry_parity_verified=true` |
| Installed-app stability | `20 passed / 0 failed` |
| Error scenarios | `passed` |
| Diagnostics package | `diagnostics_ok=true` |
| Uninstall | `uninstall_ok=true` |
| Reinstall | `reinstall_ok=true` |

## Deliverables

| Artifact | Bytes | SHA256 |
|---|---:|---|
| `dist/SolidWorks AI Studio Setup.exe` | 132,941,810 | `c5cb3034029a98f62c9a56cd2ea881be85942e857d56f184965944896c6b3ee7` |
| `dist/SolidWorks AI Studio Portable.exe` | 132,719,884 | `4ffa7ea39459bc9f6c9f030e78d4a3cf7c2bd45e663e19efcd135741ae394ef4` |
| `dist/SolidWorks AI Studio Setup.exe.blockmap` | 139,906 | `36733061ef5ff0abdf86f3a7b91184995ffb4f46889dfd9ffd2a5830c65cb6c5` |
| `outputs/v095_rc2/latest/SolidWorks-AI-Studio-v0.9.5-rc.2-windows-x64.zip` | 265,818,537 | `ec4f312a168b97518148651931cded131d1fe55d8ad15c7e24faa764541d24ab` |
| `outputs/v095_rc2/latest/SolidWorks-AI-Studio-v0.9.5-rc.2-diagnostics.zip` | 17,185 | `f236ff57d5552121ef2a38e31a8f881cad9600c39e4fa301f473e9a8134410cc` |

## Evidence Package

Redacted evidence lives under:

```text
release_evidence/v0.9.5-rc.2/
```

Full generated evidence and deliverables live under ignored outputs:

```text
outputs/v095_rc2/latest/
```

Large EXE zips, CAD outputs, screenshots, Electron user-data, and API keys are not committed.

## Known Limits

- Error scenarios that would destructively alter the user's SolidWorks session or template configuration are reported as `skipped_with_reason`.
- One low-severity esbuild development-server advisory remains; `npm audit --audit-level=high` passes.
