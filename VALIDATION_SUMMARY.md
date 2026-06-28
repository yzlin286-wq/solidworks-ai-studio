# Validation Summary

This file separates archived v0.9.0 evidence from the current recovered source baseline. The archived values below are historical validation evidence only; they must not be reported as current source validation until the restored Workbench code is revalidated in this repository.

## Recovery Incident

During v0.9.1 hardening, an early cleanup script revision removed workspace files too broadly. The current source tree was recovered by creating a fresh clone from the public GitHub repository and copying the v0.9.1 hardening files back in while excluding `.git`, `node_modules`, `.venv`, `dist`, `outputs`, `.pytest_cache`, and `test-results`. Some local, uncommitted v0.9.0 AI Capability Workbench source files were not present in the public repository and must be restored or rebuilt before v0.9.2 can be marked complete.

## Archived v0.9.0 Evidence

| Area | Result |
|---|---:|
| Backend pytest | 35 passed |
| Frontend Vitest | 7 passed |
| Playwright smoke | 1 passed |
| Packaged EXE runtime | `packaged_exe_ok=true` |
| LLM provider test | `llm_connection_ok=true` |
| Vision validation | `visual_ok=true`, `degraded=false` |
| AI capabilities | 27 |
| Recipes | 14 |
| MCP tools | 16 |
| Low-level main nav entries | 0 |
| MCP snippets visible | 5 snippets, copy action visible |
| Secret scan | 0 real key hits |

## Current Recovered Baseline

| Area | Result |
|---|---:|
| Fresh clone source | restored from `yzlin286-wq/solidworks-ai-studio` |
| v0.9.1 hardening docs/scripts | copied into fresh clone |
| AI Capability Workbench source | restored/rebuilt in current source |
| Backend pytest after recovery | 35 passed |
| Frontend TypeScript typecheck | passed |
| Frontend Vitest after recovery | 7 passed |
| Playwright smoke after recovery | 1 passed |
| Registry entries | 27 AI capabilities |
| Recipe entries | 14 recipes |
| MCP tools | 16 real tools |
| Low-level main nav entries | 0 |
| Mock mounting_plate workflow | completed through plan -> generate script -> static validation -> approval -> execute -> artifacts |
| Mock mounting_plate task ID | `d6fb36cc9181401193c27daf4efb2261` |
| Packaged EXE smoke | `packaged_exe_ok=true` |
| Packaged screenshots | 7 app screenshots |
| npm audit high | passed, only low esbuild dev-server advisory remains |
| Electron icon config | custom `apps/desktop/build/icon.ico` configured |
| Real SolidWorks preflight | connected, revision `33.5.0` |
| Real mounting_plate task ID | `b284ae411c9145f1b0f85b5ed63a61a6` |
| Real mounting_plate verification | `real_execution_verified=true`, `hole_features_restored=true`, `geometry_parity_verified=true` |
| Long stability | `20 passed / 0 failed`, every run observed 4 holes |

## v0.9.4 End-to-End Usable App Evidence

This is current evidence from the packaged application, not archived v0.9.0 evidence.

| Area | Result |
|---|---:|
| Packaged backend build | passed |
| Packaged desktop build | passed |
| Packaged EXE launch | `ok=true` |
| Packaged artifacts | `dist/SolidWorks AI Studio Setup.exe`, `dist/SolidWorks AI Studio Portable.exe`, `dist/win-unpacked/SolidWorks AI Studio.exe` |
| Evidence report | `outputs/v094_e2e/latest/V094_E2E_USABLE_APP_REPORT.json` |
| Text model configured | `glm-5.1` |
| Text LLM verified | `chat_verified=true` |
| Vision model configured | `doubao-seed-2.0-pro` |
| Vision LLM verified | `vision_verified=true` |
| Visual validation | `visual_ok=true`, `degraded=false`, `vision_analysis_count=8` |
| SolidWorks preflight | `can_run_real_com=true`, revision `33.5.0` |
| Natural language run ID | `be5b5647068c4d288b029e9dc1a70c63` |
| Natural language run | `stage=done`, `real_execution_verified=true` |
| Workbench task ID | `f1eff04e57d4490f91d0627cae83dcf2` |
| Workbench execution | `real_execution_verified=true` |
| Geometry evidence | `hole_features_restored=true`, `geometry_parity_verified=true` |
| Workbench artifacts | 9 artifacts |
| Task History API | `task_history_api_visible=true` |
| Task History UI | `task_history_visible=true` |
| Packaged screenshots | 7 pages, all assertions passed |
| Script | `scripts/v094_e2e_usable_app_validation.mjs` |

### v0.9.4 Packaged Page Coverage

| Page | Evidence |
|---|---:|
| Dashboard | screenshot assertion passed |
| Settings model configuration | screenshot assertion passed |
| Settings verified state | screenshot assertion passed |
| AI CAD Studio / Capability Workbench | screenshot assertion passed |
| Task History | screenshot assertion passed |
| Integration | screenshot assertion passed |
| Developer | screenshot assertion passed |

## v0.9.5 RC Freeze Evidence

This is current RC freeze evidence generated after rebuilding the packaged artifacts at version `0.9.5-rc.1`.

| Area | Result |
|---|---:|
| RC verdict | `RC PASS` |
| Root package version | `0.9.5-rc.1` |
| Desktop package version | `0.9.5-rc.1` |
| Backend API version | `0.9.5-rc.1` |
| Branch | `codex/v0.9.5-release-candidate-freeze` |
| Release artifact hashes | `release_evidence/v0.9.5-rc.1/SHA256SUMS.txt` |
| Redacted evidence package | `release_evidence/v0.9.5-rc.1/` |
| Full generated evidence package | `outputs/v095_rc/latest/evidence_package/` |
| Installer first start | `ok=true` |
| Fresh user config | no API key preloaded |
| First-start backend health | `ok=true`, version `0.9.5-rc.1` |
| Packaged E2E | `ok=true` |
| Text model | `glm-5.1`, `chat_verified=true` |
| Vision model | `doubao-seed-2.0-pro`, `vision_verified=true` |
| Visual validation | `visual_ok=true`, `degraded=false`, `vision_analysis_count=8`, `vision_error_count=0` |
| SolidWorks preflight | `can_run_real_com=true`, revision `33.5.0` |
| Natural-language run ID | `744ada29452d41c89f147efd9376edb5` |
| Natural-language run | `stage=done`, `real_execution_verified=true` |
| Workbench task ID | `a101d773c84141cbbcbc7521a81faabb` |
| Workbench execution | `real_execution_verified=true` |
| Geometry evidence | `hole_features_restored=true`, `geometry_parity_verified=true` |
| Task History API/UI | visible |

### v0.9.5 RC Release Artifacts

| Artifact | SHA256 |
|---|---|
| `dist/SolidWorks AI Studio Setup.exe` | `d36f9a4d9118615db99ec4719a3e93124c98a2788a2f1f704e465facde44c08f` |
| `dist/SolidWorks AI Studio Portable.exe` | `9edc074eaa5db01df399ba0a0451ddda18f4aca8cb23898a6bf849738c3ac704` |
| `dist/SolidWorks AI Studio Setup.exe.blockmap` | `b17bafd5abe26134f8b83120667a2437063269a96990b28a32846408b778c7ca` |
| `dist/win-unpacked/SolidWorks AI Studio.exe` | `e28e34ab6bec280d41dcf02910c4f3aea2d8c1fa9382f5c288aa0601d4c3fe01` |

## Archived Real SolidWorks Evidence

- SolidWorks revision: `33.5.0`.
- Real task ID: `1aad1cc4590449d28c0ae15fb45c8d77`.
- Execution mode: `real`.
- Real execution verified: `true`.
- Mock/Demo: `false`.

### Real Task Artifacts

| Artifact | Evidence |
|---|---:|
| `mounting_plate.SLDPRT` | 78,226 bytes |
| `mounting_plate.STEP` | 37,006 bytes |
| `mounting_plate_parameters.json` | 323 bytes |
| `mounting_plate_review_report.json` | 4,917 bytes |
| `mounting_plate_review_summary.md` | 968 bytes |
| `mounting_plate_isometric.bmp` | 4,800,054 bytes |
| `mounting_plate_front.bmp` | 4,800,054 bytes |
| `mounting_plate_top.bmp` | 4,800,054 bytes |
| `mounting_plate_right.bmp` | 4,800,054 bytes |

## Current Real SolidWorks Evidence

- SolidWorks revision: `33.5.0`.
- Real task ID: `b284ae411c9145f1b0f85b5ed63a61a6`.
- Execution mode: `real`.
- Real execution verified: `true`.
- Geometry parity verified: `true`.
- Hole features restored: `true`.
- Hole count expected/observed: `4 / 4`.
- Hole diameter: `6.5 mm`.
- Hole offset from plate corners: `10.0 mm`.
- Hole centers: `(-50, -30)`, `(50, -30)`, `(50, 30)`, `(-50, 30)` mm for a `120 x 80 x 10 mm` plate.
- Evidence reports regenerated under `outputs/validation/latest/MOUNTING_PLATE_GEOMETRY_PARITY_TASK.json` and `outputs/validation/latest/LONG_STABILITY_MOUNTING_PLATE_REPORT.json`.

### Current Real Task Artifacts

| Artifact | Evidence |
|---|---:|
| `mounting_plate.SLDPRT` | 77,787 bytes |
| `mounting_plate.STEP` | 37,028 bytes |
| `mounting_plate_parameters.json` | 149 bytes |
| `mounting_plate_review_review_report.json` | 4,845 bytes |
| `mounting_plate_review_review_summary.md` | 1,108 bytes |
| `mounting_plate_review_front.bmp` | 4,800,054 bytes |
| `mounting_plate_review_isometric.bmp` | 4,800,054 bytes |
| `mounting_plate_review_right.bmp` | 4,800,054 bytes |
| `mounting_plate_review_top.bmp` | 4,800,054 bytes |

### v0.9.3 Geometry Parity Long-Stability Evidence

| Area | Result |
|---|---:|
| Script | `scripts/solidworks_long_stability_mounting_plate.ps1 -Count 20` |
| Status | `passed` |
| Pass / fail | `20 / 0` |
| First task ID | `4a4f7849752242269d0bad3483637659` |
| Last task ID | `0a961b8053214079b76550454e9236fb` |
| Artifact count per run | `9` |
| Geometry parity per run | `hole_features_restored=true`, `geometry_parity_verified=true`, `hole_count_observed=4` |

## Current Recipe Validation Matrix

| recipe_id | capability_id | mock_plan | mock_execute | real_solidworks_execute | artifacts | review_report | maturity | known_limits |
|---|---|---:|---:|---:|---|---:|---|---|
| `basic_box` | `ai.parametric_part_generator` | pass | pass | not_run | `box.SLDPRT`, `box.STEP`, `box_parameters.json` | placeholder | stable | Real execution needs recipe-specific SolidWorks script expansion. |
| `cylinder` | `ai.parametric_part_generator` | pass | pass | not_run | `cylinder.SLDPRT`, `cylinder.STEP`, `cylinder_parameters.json` | placeholder | stable | Real execution needs recipe-specific SolidWorks script expansion. |
| `mounting_plate` | `ai.parametric_part_generator` | pass | pass | pass | `mounting_plate.SLDPRT`, `mounting_plate.STEP`, parameters JSON, review JSON/Markdown, 4 previews | pass | stable | v0.9.3 restored four-corner through-hole geometry; long-stability script now requires parity evidence. |
| `flange_plate` | `ai.parametric_part_generator` | pass | pass | not_run | `flange_plate.SLDPRT`, `flange_plate.STEP`, `flange_parameters.json` | placeholder | stable | Real execution needs flange-specific feature script. |
| `l_bracket` | `ai.complex_mechanical_part_generator` | pass | pass | not_run | `l_bracket.SLDPRT`, `l_bracket.STEP`, `review_report.json` | placeholder | beta | Real execution requires additional stable edge/feature selection. |
| `shaft` | `ai.shaft_revolved_part_generator` | pass | pass | not_run | `shaft.SLDPRT`, `shaft.STEP`, `shaft_parameters.json` | placeholder | beta | Real execution requires revolved-profile script hardening. |
| `cnc_mount` | `ai.cnc_machined_part_generator` | pass | pass | not_run | `cnc_mount.SLDPRT`, `cnc_mount.STEP`, `review_report.json` | placeholder | experimental | Depends on CNC subskill; real repeated validation pending. |
| `threaded_hole_block` | `ai.threaded_hole_engineering` | pass | pass | partial | `threaded_hole_block.SLDPRT`, `threaded_hole_block.STEP`, parameters, review | placeholder | experimental | Shares mounting-plate real script path today; full thread-feature semantics pending. |
| `basic_assembly` | `ai.assembly_generator` | pass | pass | not_run | `basic_assembly.SLDASM`, `assembly_report.json` | placeholder | stable | Real execution requires assembly file inputs and mate evidence. |
| `motion_ready_fan` | `ai.motion_ready_assembly_generator` | pass | pass | not_run | `motion_ready_fan.SLDASM`, `mate_summary.json`, `review_report.json` | placeholder | experimental | Requires motion-ready assembly evidence and optional Motion add-in. |
| `three_view_drawing_pdf` | `ai.drawing_bom_pdf_assistant` | pass | pass | not_run | `three_view.SLDDRW`, `three_view.PDF`, `bom.json` | placeholder | beta | Requires source part/assembly and drawing template state. |
| `export_current_document` | `ai.smart_export_batch_converter` | pass | pass | not_run | `export.STEP`, `export.STL`, `export_manifest.json` | placeholder | stable | Requires active document; direct export is approval-gated. |
| `batch_export` | `ai.smart_export_batch_converter` | pass | pass | not_run | `batch_export_manifest.json` | placeholder | stable | Requires controlled input folder and per-file failure accounting. |
| `review_current_document` | `ai.result_review_assistant` | pass | pass | not_run | `review_report.json`, `preview_iso.png`, `preview_front.png` | pass/placeholder | stable | Requires active document for real review; otherwise skipped with reason. |

## Current Missing Revalidation Items

- Generated validation outputs remain uncommitted by design and must be regenerated from the commands below.
- MCP `solidworks_review_active` can still emit manual-preview warnings; v0.9.4 visual acceptance is based on the packaged visual-validation report and Workbench real evidence.
- The validation API key is required through local config or `SWAI_VALIDATION_API_KEY`; it is not committed.

## Evidence Commands

```powershell
$env:PYTHONPATH="$PWD\backend"
python -m pytest backend/tests -q
npm run typecheck --workspace apps/desktop
npm test --workspace apps/desktop
npm run smoke --workspace apps/desktop
powershell -ExecutionPolicy Bypass -File scripts\build_backend.ps1
powershell -ExecutionPolicy Bypass -File scripts\build_desktop.ps1
node scripts\v095_install_first_start_validation.mjs
node scripts\v094_e2e_usable_app_validation.mjs
node scripts\create_v095_rc_evidence_package.mjs
node scripts\packaged_exe_visual_validation.mjs
powershell -ExecutionPolicy Bypass -File scripts\sw2025_preflight.ps1
powershell -ExecutionPolicy Bypass -File scripts\solidworks_long_stability_mounting_plate.ps1 -Count 20
```

## Release Hardening Notes

- Generated artifacts are excluded from source release and can be regenerated by validation scripts.
- API keys must remain in local user config or environment variables only.
- Real SolidWorks validation must fail or skip with explicit reason when COM/add-ins/templates are not ready.
- npm audit high finding is addressed by Electron `42.5.0`.
- One low-severity esbuild development-server advisory may remain depending on the installed Vite/esbuild tree; it does not affect packaged runtime and should be revisited when Vite releases a compatible fix.
