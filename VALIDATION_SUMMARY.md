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
| Backend pytest after recovery | 29 passed |
| Frontend Vitest after recovery | 5 passed |
| Playwright smoke after recovery | 1 passed |
| npm audit high | passed, only low esbuild dev-server advisory remains |
| Electron icon config | custom `apps/desktop/build/icon.ico` configured |
| Missing current revalidation | AI Workbench source restore, 27 capabilities, 14 recipes, packaged smoke, real SolidWorks mounting plate, 20-run long stability |

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

## Archived Recipe Validation Matrix

| recipe_id | capability_id | mock_plan | mock_execute | real_solidworks_execute | artifacts | review_report | maturity | known_limits |
|---|---|---:|---:|---:|---|---:|---|---|
| `basic_box` | `ai.parametric_part_generator` | pass | pass | not_run | `box.SLDPRT`, `box.STEP`, `box_parameters.json` | placeholder | stable | Real execution needs recipe-specific SolidWorks script expansion. |
| `cylinder` | `ai.parametric_part_generator` | pass | pass | not_run | `cylinder.SLDPRT`, `cylinder.STEP`, `cylinder_parameters.json` | placeholder | stable | Real execution needs recipe-specific SolidWorks script expansion. |
| `mounting_plate` | `ai.parametric_part_generator` | pass | pass | pass | `mounting_plate.SLDPRT`, `mounting_plate.STEP`, parameters JSON, previews | pass | stable | Primary real MVP path; long-stability script covers repeated execution. |
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

- Restore or rebuild `/api/ai-capabilities` and task workflow source.
- Revalidate 27 AI Capability registry entries and 14 Recipe registry entries from current source.
- Revalidate Dashboard, grouped sidebar, capability group/detail pages, and task history.
- Re-run mock mounting_plate plan/script/validate/approve/execute/artifacts.
- Re-run packaged EXE smoke and visual checks.
- Re-run real SolidWorks mounting_plate with `real_execution_verified=true`.
- Re-run `scripts/solidworks_long_stability_mounting_plate.ps1 -Count 20`.

## Evidence Commands

```powershell
$env:PYTHONPATH="$PWD\backend"
python -m pytest backend/tests -q
npm run typecheck --workspace apps/desktop
npm test --workspace apps/desktop
npm run smoke --workspace apps/desktop
powershell -ExecutionPolicy Bypass -File scripts\build_backend.ps1
powershell -ExecutionPolicy Bypass -File scripts\build_desktop.ps1
powershell -ExecutionPolicy Bypass -File scripts\run_packaged_exe_visual_validation.ps1
```

## Release Hardening Notes

- Generated artifacts are excluded from source release and can be regenerated by validation scripts.
- API keys must remain in local user config or environment variables only.
- Real SolidWorks validation must fail or skip with explicit reason when COM/add-ins/templates are not ready.
- npm audit high finding is addressed by Electron `42.5.0`.
- One low-severity esbuild development-server advisory may remain depending on the installed Vite/esbuild tree; it does not affect packaged runtime and should be revisited when Vite releases a compatible fix.
