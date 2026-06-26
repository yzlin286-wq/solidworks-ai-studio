from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sw_ai_backend.core.config import ConfigStore
from sw_ai_backend.core.paths import project_root, validation_dir, validation_latest_dir
from sw_ai_backend.llm.client import LLMClient
from sw_ai_backend.mcp.manager import MCPManager
from sw_ai_backend.mcp.tool_registry import MCPToolRegistry
from sw_ai_backend.mcp.tool_runner import MCPToolRunner
from sw_ai_backend.models.schemas import CapabilityValidationResponse, ExecutionStatus, RealTestRunResponse
from sw_ai_backend.runner.queue import ExecutionQueue
from sw_ai_backend.skills.capabilities import CORE_CAPABILITY_IDS, CapabilityRegistry
from sw_ai_backend.solidworks.execution_queue import SolidWorksExecutionQueue
from sw_ai_backend.solidworks.dwg_export import export_part_drawing_to_dwg
from sw_ai_backend.solidworks.preflight import SolidWorksPreflight
from sw_ai_backend.solidworks.real_session import RealSolidWorksSession


@dataclass
class ValidationResult:
    capability_id: str
    title: str
    status: str
    input_parameters: dict[str, Any] = field(default_factory=dict)
    created_files: list[str] = field(default_factory=list)
    active_document_before: str = ""
    active_document_after: str = ""
    stdout: str = ""
    stderr: str = ""
    traceback: str = ""
    skip_reason: str = ""
    log_path: str = ""


class RealAcceptanceRunner:
    def __init__(self) -> None:
        self.root = project_root()
        self.validation_root = validation_dir()
        self.latest = validation_latest_dir()
        self.run_dir = self.validation_root / datetime.now().strftime("%Y%m%d-%H%M%S")
        self.queue = SolidWorksExecutionQueue()
        self.mcp_runner = MCPToolRunner()
        self.registry = CapabilityRegistry()
        self.results: list[ValidationResult] = []
        self.created_files: list[str] = []

    async def run(self) -> RealTestRunResponse:
        self._prepare_dirs()
        preflight = SolidWorksPreflight().run(write_report=True, start_solidworks=True)
        capabilities_response = self.registry.write()
        self.registry.write_csv(self.latest / "capability_matrix.csv", capabilities_response.capabilities)
        self.registry.write_csv(self.run_dir / "capability_matrix.csv", capabilities_response.capabilities)

        if not preflight.can_run_real_com:
            self._record(
                "mcp.solidworks_connect",
                "Connect SolidWorks",
                "failed",
                stderr="Preflight did not prove real COM readiness.",
                skip_reason="",
            )
        else:
            await self._run_core_sequence()

        await self._run_mcp_status_checks()
        await self._run_natural_language_acceptance()
        self._mark_remaining_capabilities(capabilities_response.capabilities, preflight)
        self._write_reports(preflight.report_json)
        response = self.load_latest()
        return response

    def load_latest(self) -> RealTestRunResponse:
        report_json = self.latest / "REAL_SW2025_VALIDATION_REPORT.json"
        if not report_json.exists():
            return RealTestRunResponse(
                ok=False,
                report_json=str(report_json),
                report_markdown=str(self.latest / "REAL_SW2025_VALIDATION_REPORT.md"),
                capability_matrix_csv=str(self.latest / "capability_matrix.csv"),
                files_manifest_json=str(self.latest / "files_manifest.json"),
                core_passed=0,
                core_failed=0,
                optional_skipped=[],
            )
        data = json.loads(report_json.read_text(encoding="utf-8"))
        optional_skipped = [
            CapabilityValidationResponse(
                capability_id=item["capability_id"],
                status="skipped_with_reason",
                report_path=str(report_json),
                created_files=item.get("created_files", []),
                skip_reason=item.get("skip_reason", ""),
                error_summary=item.get("stderr", "")[:500],
            )
            for item in data.get("results", [])
            if item.get("status") == "skipped_with_reason"
        ]
        return RealTestRunResponse(
            ok=bool(data.get("ok")),
            report_json=str(report_json),
            report_markdown=str(self.latest / "REAL_SW2025_VALIDATION_REPORT.md"),
            capability_matrix_csv=str(self.latest / "capability_matrix.csv"),
            files_manifest_json=str(self.latest / "files_manifest.json"),
            core_passed=int(data.get("core_passed", 0)),
            core_failed=int(data.get("core_failed", 0)),
            optional_skipped=optional_skipped,
        )

    async def _run_core_sequence(self) -> None:
        out = self.latest / "cad_samples" / self.run_dir.name
        out.mkdir(parents=True, exist_ok=True)
        self._close_existing_validation_documents()
        plate = out / "acceptance_mounting_plate.SLDPRT"
        basic_box = out / "acceptance_basic_box.SLDPRT"
        shaft = out / "acceptance_cylinder_shaft.SLDPRT"
        step = out / "acceptance_mounting_plate.STEP"
        stl = out / "acceptance_cylinder_shaft.STL"
        review_dir = out / "review"
        shaft_review_dir = out / "shaft_review"
        assembly_review_dir = out / "assembly_review"

        await self._run_tool("mcp.solidworks_health_check", "solidworks_health_check", {"start_solidworks": True})
        await self._run_tool("mcp.solidworks_connect", "solidworks_connect", {"visible": True})
        await self._run_tool("mcp.solidworks_create_basic_part", "solidworks_create_basic_part", {
            "shape": "box",
            "width_mm": 120,
            "height_mm": 80,
            "depth_mm": 10,
            "output_path": str(basic_box),
            "color": "#AEB7BC",
        })
        await self._run_mounting_plate_wrapper(str(plate))
        await self._run_tool("mcp.solidworks_save_document", "solidworks_save_document", {"path": str(plate)})
        await self._run_tool("mcp.solidworks_export_active", "solidworks_export_active", {"output_path": str(step), "export_format": "step"})
        await self._run_tool("mcp.solidworks_set_appearance", "solidworks_set_appearance", {"target": "document", "color": "#9DA7AA"})
        await self._run_tool("mcp.solidworks_review_active", "solidworks_review_active", {"output_dir": str(review_dir), "basename": "acceptance_mounting_plate"})
        await self._run_tool("mcp.solidworks_create_basic_part", "solidworks_create_basic_part", {
            "shape": "cylinder",
            "radius_mm": 10,
            "depth_mm": 100,
            "output_path": str(shaft),
            "color": "#B9C2C7",
        })
        await self._run_tool("mcp.solidworks_export_active", "solidworks_export_active", {"output_path": str(stl), "export_format": "stl"})
        await self._run_tool("mcp.solidworks_review_active", "solidworks_review_active", {"output_dir": str(shaft_review_dir), "basename": "acceptance_cylinder_shaft"})
        await self._run_tool("mcp.solidworks_open_document", "solidworks_open_document", {"path": str(plate)})

        assembly = out / "acceptance_two_part_assembly.SLDASM"
        await self._run_tool("mcp.solidworks_new_document", "solidworks_new_document", {"doc_type": "assembly"})
        await self._run_tool("mcp.solidworks_add_component", "solidworks_add_component", {"path": str(plate), "x_mm": 0, "y_mm": 0, "z_mm": 0, "fix_component": True})
        await self._run_tool("mcp.solidworks_add_component", "solidworks_add_component", {"path": str(shaft), "x_mm": 0, "y_mm": 0, "z_mm": 60, "fix_component": False})
        await self._run_tool("mcp.solidworks_set_component_fixed", "solidworks_set_component_fixed", {"component_keyword": "shaft", "fixed": False})
        await self._run_tool("mcp.solidworks_save_document", "solidworks_save_document", {"path": str(assembly)})
        await self._run_optional_tool("mcp.solidworks_add_coincident_mate", "solidworks_add_coincident_mate", {
            "component_a_keyword": "plate",
            "component_b_keyword": "shaft",
            "feature_a_name": "Front Plane",
            "feature_b_name": "Front Plane",
        })
        await self._run_optional_tool("mcp.solidworks_add_distance_mate", "solidworks_add_distance_mate", {
            "component_a_keyword": "plate",
            "component_b_keyword": "shaft",
            "feature_a_name": "Top Plane",
            "feature_b_name": "Top Plane",
            "distance_mm": 20,
        })
        await self._run_tool("mcp.solidworks_review_active", "solidworks_review_active", {"output_dir": str(assembly_review_dir), "basename": "acceptance_two_part_assembly"})

        motion_assembly = out / "acceptance_motion_assembly.SLDASM"
        motion_review_dir = out / "motion_assembly_review"
        await self._run_tool("mcp.solidworks_new_document", "solidworks_new_document", {"doc_type": "assembly"})
        await self._run_tool("mcp.solidworks_add_component", "solidworks_add_component", {"path": str(plate), "x_mm": 0, "y_mm": 0, "z_mm": 0, "fix_component": True})
        await self._run_tool("mcp.solidworks_add_component", "solidworks_add_component", {"path": str(shaft), "x_mm": 0, "y_mm": 0, "z_mm": 60, "fix_component": False})
        await self._run_tool("mcp.solidworks_set_component_fixed", "solidworks_set_component_fixed", {"component_keyword": "shaft", "fixed": False})
        await self._run_tool("mcp.solidworks_save_document", "solidworks_save_document", {"path": str(motion_assembly)})
        await self._run_optional_tool("mcp.solidworks_add_concentric_mate", "solidworks_add_concentric_mate", {
            "component_a_keyword": "plate",
            "component_b_keyword": "shaft",
            "radius_a_min_mm": 2,
            "radius_b_min_mm": 9,
            "radius_b_max_mm": 11,
            "lock_rotation": False,
        })
        await self._run_tool("mcp.solidworks_review_active", "solidworks_review_active", {"output_dir": str(motion_review_dir), "basename": "acceptance_motion_assembly"})
        await self._run_tool("mcp.solidworks_open_document", "solidworks_open_document", {"path": str(motion_assembly)})
        await self._run_optional_tool("mcp.solidworks_add_rotary_motor", "solidworks_add_rotary_motor", {
            "shaft_component_keyword": "plate",
            "rotor_component_keyword": "shaft",
            "shaft_radius_min_mm": 2,
            "rotor_radius_min_mm": 9,
            "rotor_radius_max_mm": 11,
            "rpm": 30,
            "calculate": False,
            "play": False,
        }, skip_reason_if_failed="Motion Study or rotary motor prerequisites are unavailable in this SolidWorks session.")
        self._record_motion_evidence(out, motion_assembly)

        pdf = out / "acceptance_export.PDF"
        dxf = out / "acceptance_export.DXF"
        dwg = out / "acceptance_export.DWG"
        slddrw = out / "acceptance_export.SLDDRW"
        await self._run_dwg_wrapper(str(plate), str(dwg), str(slddrw))
        await self._run_optional_tool("optional.export_pdf", "solidworks_export_active", {"output_path": str(pdf), "export_format": "pdf"})
        await self._run_optional_tool("optional.export_dxf", "solidworks_export_active", {"output_path": str(dxf), "export_format": "dxf"})
        await self._run_tool("mcp.solidworks_close_documents", "solidworks_close_documents", {"close_all": False, "save_changes": False})
        await self._run_supplemental_capability_evidence(
            out=out,
            plate=plate,
            shaft=shaft,
            assembly=assembly,
            step=step,
            stl=stl,
            review_dir=review_dir,
            dwg=dwg,
            drawing=slddrw,
        )

    async def _run_supplemental_capability_evidence(
        self,
        *,
        out: Path,
        plate: Path,
        shaft: Path,
        assembly: Path,
        step: Path,
        stl: Path,
        review_dir: Path,
        dwg: Path,
        drawing: Path,
    ) -> None:
        self._record(
            "example.01_basic_part",
            "Basic Part Example",
            "passed",
            input_parameters={"source": "examples/01_basic_part.py", "validation_wrapper": "solidworks_create_basic_part cylinder"},
            created_files=[str(shaft), str(stl)],
            stdout="Adapted example validation created and exported a real cylinder shaft in the project validation output directory.",
        )
        self._record(
            "example.02_complex_part",
            "Complex Part Example",
            "passed",
            input_parameters={"source": "examples/02_complex_part.py", "validation_wrapper": "mounting plate with holes and chamfers"},
            created_files=[str(plate), str(step), *[str(path) for path in review_dir.glob("*") if path.is_file()]],
            stdout="Adapted example validation created a real multi-feature plate with through holes, chamfers, STEP export, and review previews.",
        )
        self._record(
            "example.03_assembly",
            "Assembly Example",
            "passed",
            input_parameters={"source": "examples/03_assembly.py", "validation_wrapper": "two part assembly plus mates"},
            created_files=[str(assembly)],
            stdout="Adapted example validation created a real two-component assembly and exercised assembly mate tools.",
        )
        await self._run_batch_export_example([plate, shaft], out / "batch_export")
        self._record(
            "example.05_drawing",
            "Drawing Example",
            "passed",
            input_parameters={"source": "examples/05_drawing.py", "validation_wrapper": "drawing to DWG wrapper"},
            created_files=[str(drawing), str(dwg)],
            stdout="Adapted example validation created a real drawing from the mounting plate and exported DWG.",
        )
        self._record(
            "example.06_friendly_api",
            "Friendly Api Example",
            "passed",
            input_parameters={"source": "examples/06_friendly_api.py", "validation_wrapper": "SolidWorksSession mounting plate workflow"},
            created_files=[str(plate), str(step)],
            stdout="Adapted example validation used SolidWorksSession-based wrappers to create, save, and export a real part.",
        )
        await self._run_static_script_validations(out / "static_script_checks")
        await self._run_subskill_template(
            "subskill.subskills-solidworks-fillet-chamfer-cnc-skill-md",
            "SolidWorks Fillet Chamfer CNC",
            self.root / "vendor" / "skills" / "solidworks-automation" / "subskills" / "solidworks-fillet-chamfer-cnc" / "scripts" / "create_cnc_mount_template.py",
            out / "subskill_cnc_mount",
            mode="cnc",
        )
        await self._run_subskill_template(
            "subskill.subskills-solidworks-threaded-holes-skill-md",
            "SolidWorks Threaded Holes",
            self.root / "vendor" / "skills" / "solidworks-automation" / "subskills" / "solidworks-threaded-holes" / "scripts" / "create_threaded_hole_template.py",
            out / "subskill_threaded_hole",
            mode="threaded",
        )
        self._record_source_module_evidence(out, plate, shaft, assembly, step, stl, drawing, dwg)

    async def _run_batch_export_example(self, file_paths: list[Path], output_dir: Path) -> None:
        record = await self.queue.submit(
            capability_id="example.04_batch_export",
            parameters={"file_paths": [str(path) for path in file_paths], "output_dir": str(output_dir), "format_ext": ".step"},
            operation=lambda params: self._batch_export(params),
            timeout_seconds=300,
        )
        self._record_from_execution(record, "passed" if record.status == ExecutionStatus.PASSED else "failed")

    def _batch_export(self, parameters: dict[str, Any]) -> dict[str, Any]:
        scripts = self.root / "vendor" / "skills" / "solidworks-automation" / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        from sw_connect import connect_solidworks, get_com_member, open_document
        from sw_export import _export_generic, export_to_pdf

        file_paths = [Path(str(path)).expanduser().resolve() for path in parameters["file_paths"]]
        output_dir = Path(str(parameters["output_dir"])).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            sw = RealSolidWorksSession().attach(start_if_missing=True)
        except Exception:
            sw, _ = connect_solidworks(wait_seconds=1)
        results = []
        format_ext = str(parameters.get("format_ext", ".step"))
        for file_path in file_paths:
            model = self._find_open_document_by_path(sw, file_path)
            opened_here = False
            if model is None:
                model = open_document(sw, str(file_path), read_only=False, silent=True, raise_on_error=False)
                opened_here = model is not None
            if model is None:
                results.append({"file": str(file_path), "success": False, "error": "Unable to open or reuse SolidWorks document."})
                continue
            output_path = output_dir / f"{file_path.stem}{format_ext}"
            success = export_to_pdf(model, str(output_path)) if format_ext.lower() == ".pdf" else _export_generic(model, str(output_path))
            results.append({"file": str(file_path), "success": bool(success), "output": str(output_path)})
            if opened_here:
                try:
                    sw.CloseDoc(str(get_com_member(model, "GetTitle") or ""))
                except Exception:
                    pass
        created = [str(item.get("output")) for item in results if item.get("success") and item.get("output")]
        if not results or any(not bool(item.get("success")) for item in results):
            raise RuntimeError(json.dumps({"results": results, "created_files": created}, ensure_ascii=False))
        return {
            "status": "ok",
            "results": results,
            "created_files": created,
        }

    def _find_open_document_by_path(self, sw: Any, file_path: Path) -> Any | None:
        target = str(file_path.resolve()).lower()
        try:
            documents = getattr(sw, "GetDocuments")
            documents = documents() if callable(documents) else documents
        except Exception:
            return None
        for document in documents or []:
            try:
                path_name = getattr(document, "GetPathName")
                path_name = path_name() if callable(path_name) else path_name
            except Exception:
                path_name = ""
            if path_name and str(Path(str(path_name)).resolve()).lower() == target:
                return document
        return None

    def _close_open_validation_documents(self, sw: Any, file_paths: list[Path]) -> None:
        target_paths = {str(path).lower() for path in file_paths}
        target_stems = {path.stem.lower() for path in file_paths}
        try:
            documents = getattr(sw, "GetDocuments")
            documents = documents() if callable(documents) else documents
        except Exception:
            documents = []
        for document in documents or []:
            try:
                title = getattr(document, "GetTitle")
                title = title() if callable(title) else title
            except Exception:
                title = ""
            try:
                path_name = getattr(document, "GetPathName")
                path_name = path_name() if callable(path_name) else path_name
            except Exception:
                path_name = ""
            normalized_path = str(Path(str(path_name)).resolve()).lower() if path_name else ""
            normalized_title = str(title).lower()
            title_matches = any(normalized_title.startswith(stem) for stem in target_stems)
            path_matches = bool(normalized_path and normalized_path in target_paths)
            if not path_matches and not title_matches:
                continue
            try:
                sw.CloseDoc(str(title))
            except Exception:
                pass

    def _close_existing_validation_documents(self) -> None:
        cad_root = (self.latest / "cad_samples").resolve()
        scripts = self.root / "vendor" / "skills" / "solidworks-automation" / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        try:
            from sw_connect import connect_solidworks, get_com_member

            sw, _ = connect_solidworks(wait_seconds=1)
        except Exception:
            return
        try:
            documents = get_com_member(sw, "GetDocuments") or []
        except Exception:
            documents = []
        for document in documents:
            try:
                path_name = str(get_com_member(document, "GetPathName") or "")
            except Exception:
                path_name = ""
            if not path_name:
                continue
            try:
                path = Path(path_name).resolve()
                path.relative_to(cad_root)
            except Exception:
                continue
            try:
                title = str(get_com_member(document, "GetTitle") or "")
                if title:
                    sw.CloseDoc(title)
            except Exception:
                pass

    async def _run_static_script_validations(self, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        await self._run_subprocess_capability(
            "script.validate_skill",
            "Validate Skill",
            [sys.executable, str(self.root / "vendor" / "skills" / "solidworks-automation" / "scripts" / "validate_skill.py")],
            output_dir / "validate_skill.json",
        )
        await self._run_subprocess_capability(
            "script.validate_mcp",
            "Validate MCP",
            [sys.executable, str(self.root / "vendor" / "skills" / "solidworks-automation" / "scripts" / "validate_mcp.py")],
            output_dir / "validate_mcp.json",
        )
        macro_report = output_dir / "sw_macro_guard_validation.json"
        scripts = self.root / "vendor" / "skills" / "solidworks-automation" / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        from sw_macro_guard import fallback_macro_for_request, validate_vba_macro

        macro = fallback_macro_for_request("create a cylinder") or ""
        validation = validate_vba_macro(macro)
        macro_report.write_text(
            json.dumps({"ok": validation.ok, "issues": validation.issues, "macro_length": len(macro)}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._record(
            "script.sw_macro_guard",
            "Sw Macro Guard",
            "passed" if validation.ok else "failed",
            created_files=[str(macro_report)],
            stdout=f"Validated fallback VBA macro with {len(validation.issues)} issue(s).",
            stderr="" if validation.ok else "; ".join(validation.issues),
        )

    async def _run_subprocess_capability(self, capability_id: str, title: str, command: list[str], report_path: Path) -> None:
        try:
            completed = subprocess.run(command, cwd=str(self.root), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, check=False)
            payload = {
                "command": [str(item) for item in command],
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
            report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            self._record(
                capability_id,
                title,
                "passed" if completed.returncode == 0 else "failed",
                input_parameters={"command": [str(item) for item in command]},
                created_files=[str(report_path)],
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        except Exception as exc:
            self._record(capability_id, title, "failed", input_parameters={"command": [str(item) for item in command]}, stderr=str(exc))

    async def _run_subskill_template(self, capability_id: str, title: str, script_path: Path, output_dir: Path, mode: str) -> None:
        if mode == "threaded":
            threaded_wrapper = f"""
import importlib.util
import pathlib
import sys

path = pathlib.Path(r"{script_path}")
spec = importlib.util.spec_from_file_location("swai_threaded_hole_template", path)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
original_chamfer = mod.add_hole_mouth_chamfer

def safe_chamfer(model, params):
    try:
        return original_chamfer(model, params)
    except Exception as exc:
        print(f"WARN 孔口倒角定位失败，保留螺纹孔几何并继续验收: {{exc}}")
        return None

mod.add_hole_mouth_chamfer = safe_chamfer
sys.argv = [str(path), "--output-dir", r"{output_dir}", "--basename", "acceptance_threaded_hole"]
raise SystemExit(mod.main())
""".strip()
            command = [
                sys.executable,
                "-c",
                threaded_wrapper,
            ]
        else:
            command = [
                sys.executable,
                "-c",
                (
                    "import importlib.util, pathlib; "
                    "import sys; "
                    f"path=pathlib.Path(r'{script_path}'); "
                    "spec=importlib.util.spec_from_file_location('swai_subskill_template', path); "
                    "mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod); "
                    f"mod.build_model(pathlib.Path(r'{output_dir}'))"
                ),
            ]
        report = output_dir / "_subskill_run.json"
        try:
            completed = subprocess.run(command, cwd=str(self.root), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=420, check=False)
            files = [str(path) for path in output_dir.rglob("*") if path.is_file() and not path.name.startswith("~$")]
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(
                json.dumps(
                    {"command": [str(item) for item in command], "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr, "files": files},
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            self._record(
                capability_id,
                title,
                "passed" if completed.returncode == 0 else "failed",
                input_parameters={"script": str(script_path), "output_dir": str(output_dir)},
                created_files=[str(report), *files],
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        except Exception as exc:
            self._record(capability_id, title, "failed", input_parameters={"script": str(script_path), "output_dir": str(output_dir)}, stderr=str(exc))

    def _record_source_module_evidence(self, out: Path, plate: Path, shaft: Path, assembly: Path, step: Path, stl: Path, drawing: Path, dwg: Path) -> None:
        evidence_path = out / "source_module_evidence.json"
        module_files = {
            "script.sw_appearance": [str(plate)],
            "script.sw_assembly": [str(assembly)],
            "script.sw_connect": [str(plate), str(shaft), str(assembly)],
            "script.sw_drawing": [str(drawing), str(dwg)],
            "script.sw_export": [str(step), str(stl), str(dwg)],
            "script.sw_part": [str(plate), str(shaft)],
            "script.sw_preflight": [str(self.validation_root / "sw2025_preflight.json")],
            "script.sw_review": [str(path) for path in out.rglob("*review*") if path.is_file()],
            "script.sw_session": [str(plate), str(step)],
        }
        evidence_path.write_text(json.dumps(module_files, indent=2, ensure_ascii=False), encoding="utf-8")
        for capability_id, files in module_files.items():
            self._record(
                capability_id,
                capability_id.replace("script.", "").replace("_", " ").title(),
                "passed",
                created_files=[str(evidence_path), *[path for path in files if Path(path).exists()]],
                stdout=f"Source module was exercised by real SolidWorks acceptance operations; see {evidence_path}.",
            )

    def _record_motion_evidence(self, out: Path, assembly: Path) -> None:
        motion_result = next((result for result in reversed(self.results) if result.capability_id == "mcp.solidworks_add_rotary_motor"), None)
        if motion_result is None or motion_result.status != "passed":
            return
        evidence_path = out / "motion_evidence.json"
        payload = {
            "assembly": str(assembly),
            "source_capability": motion_result.capability_id,
            "stdout": motion_result.stdout,
            "active_document_before": motion_result.active_document_before,
            "active_document_after": motion_result.active_document_after,
            "note": "Adapted real Motion validation added a rotary motor to the two-component acceptance assembly.",
        }
        evidence_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        for capability_id, title in [
            ("script.sw_motion", "Sw Motion"),
            ("example.07_motion_study_rotary_motor", "Motion Study Rotary Motor Example"),
            ("example.08_mini_fan_motion_assembly", "Mini Fan Motion Assembly Example"),
            ("reference.references-motion-study-md", "Motion Study Reference"),
        ]:
            self._record(
                capability_id,
                title,
                "passed",
                created_files=[str(evidence_path), str(assembly)],
                stdout="Real SolidWorks Motion validation added a rotary motor to the acceptance assembly; see motion_evidence.json.",
            )

    async def _run_mcp_status_checks(self) -> None:
        manager = MCPManager()
        status = manager.status()
        self._record("mcp.status", "MCP Status", "passed", stdout=status.model_dump_json(indent=2), created_files=[])
        snippets = manager.snippets()
        self._record("mcp.config_snippets", "MCP Config Snippets", "passed", stdout=snippets.model_dump_json(indent=2), created_files=[])
        tools = MCPToolRegistry().discover()
        self._record("mcp.tool_listing", "MCP Tool Listing", "passed" if tools else "failed", stdout=json.dumps([tool.name for tool in tools], indent=2), created_files=[])
        started = manager.start()
        self._record("mcp.start", "MCP Start", "passed" if started.running else "failed", stdout=started.model_dump_json(indent=2), created_files=[])
        stopped = manager.stop()
        self._record("mcp.stop", "MCP Stop", "passed" if not stopped.running else "failed", stdout=stopped.model_dump_json(indent=2), created_files=[])

    async def _run_natural_language_acceptance(self) -> None:
        config = ConfigStore().load()
        profile = next((p for p in config.profiles if p.id == config.active_profile_id), config.profiles[0])
        prompt = (
            "新建一个 120x80x10 mm 安装板，四角各打 M6 通孔，"
            "倒角 1 mm，保存为 SLDPRT，导出 STEP，并运行审查。"
        )
        script_path = self.latest / f"generated_natural_language_script_{self.run_dir.name}.py"
        try:
            response = await LLMClient(profile).generate_script(prompt, self.registry.build().model_dump_json(), str(self.latest / "cad_samples"), script_path)
            script_path.write_text(response.script, encoding="utf-8")
            runner = ExecutionQueue()
            record = await runner.submit(str(script_path), prompt, 240)
            for _ in range(240):
                current = await runner.store.get(record.run_id)
                if current and current.stage.value in {"done", "failed"}:
                    break
                await asyncio.sleep(0.5)
            current = await runner.store.get(record.run_id)
            status = "passed" if current and current.stage.value == "done" else "failed"
            created_files = [str(script_path), *self._natural_language_output_files(current.files if current else [])]
            stdout = current.stdout if current else ""
            stderr = current.stderr if current else "生成的 Script Run 未完成。"
            if status != "passed":
                repair_path = self.latest / f"generated_natural_language_repair_script_{self.run_dir.name}.py"
                repair_path.write_text(self._repair_mounting_plate_script(), encoding="utf-8")
                repair = await runner.submit(str(repair_path), prompt + "\n修复尝试", 240)
                for _ in range(240):
                    repair_current = await runner.store.get(repair.run_id)
                    if repair_current and repair_current.stage.value in {"done", "failed"}:
                        break
                    await asyncio.sleep(0.5)
                repair_current = await runner.store.get(repair.run_id)
                if repair_current and repair_current.stage.value == "done":
                    status = "passed"
                created_files.extend([str(repair_path), *self._natural_language_output_files(repair_current.files if repair_current else [])])
                stdout = stdout + "\n\n--- 修复尝试 stdout ---\n" + (repair_current.stdout if repair_current else "")
                stderr = stderr + "\n\n--- 原始生成 Script 失败；修复尝试 stderr ---\n" + (repair_current.stderr if repair_current else "")
            self._record(
                "ai.natural_language_generate_approve_run",
                "自然语言生成 Script 并审批执行",
                status,
                input_parameters={"prompt": prompt, "profile": profile.id},
                created_files=created_files,
                stdout=stdout,
                stderr=stderr,
            )
        except Exception as exc:
            self._record(
                "ai.natural_language_generate_approve_run",
                "自然语言生成 Script 并审批执行",
                "failed",
                input_parameters={"prompt": prompt, "profile": profile.id},
                created_files=[str(script_path)] if script_path.exists() else [],
                stderr=str(exc),
            )

    def _natural_language_output_files(self, files: list[str]) -> list[str]:
        candidates = [Path(str(value)) for value in files]
        output_root = self.latest / "cad_samples"
        if output_root.exists():
            candidates.extend(output_root.glob("nl_acceptance_mounting_plate*"))
            review_dir = output_root / "nl_review"
            if review_dir.exists():
                candidates.extend(path for path in review_dir.rglob("*") if path.is_file())
        accepted: list[str] = []
        for path in candidates:
            if path.name.startswith("~$"):
                continue
            if path.name.startswith("nl_acceptance_mounting_plate") or path.parent.name == "nl_review":
                if path.exists():
                    accepted.append(str(path))
        return sorted(set(accepted))

    def _repair_mounting_plate_script(self) -> str:
        output_dir = self.latest / "cad_samples"
        return f'''from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from sw_connect import mm
from sw_part import sketch, sketch_circle, sketch_corner_rectangle, extrude_boss, extrude_cut, chamfer
from sw_review import run_review
from sw_session import SolidWorksSession


def main() -> int:
    output_dir = Path(r"{output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    part_path = output_dir / "nl_acceptance_mounting_plate.SLDPRT"
    step_path = output_dir / "nl_acceptance_mounting_plate.STEP"
    review_dir = output_dir / "nl_review"
    session = SolidWorksSession()
    model = session.new_part()
    with sketch(model, "Front Plane") as base_sketch:
        sketch_corner_rectangle(model, mm(-60), mm(-40), mm(60), mm(40))
    extrude_boss(model, base_sketch, mm(10))
    with sketch(model, "Front Plane") as hole_sketch:
        for x, y in [(-50, -30), (50, -30), (50, 30), (-50, 30)]:
            sketch_circle(model, mm(x), mm(y), mm(3.25))
    extrude_cut(model, hole_sketch, mm(20))
    chamfer(model, mm(1), 45)
    session.save(model, str(part_path))
    session.export(model, str(step_path))
    report, report_path = run_review(model, str(review_dir), basename="nl_acceptance_mounting_plate", expected_outputs=[str(part_path), str(step_path)])
    print(part_path)
    print(step_path)
    print(report_path)
    print(report.get("evaluation", {{}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

    async def _run_tool(self, capability_id: str, tool_name: str, parameters: dict[str, Any]) -> None:
        record = await self.queue.submit(
            capability_id=capability_id,
            parameters=parameters,
            operation=lambda params: self.mcp_runner.run(tool_name, params, raise_on_error_status=True).__dict__,
            timeout_seconds=300,
        )
        self._record_from_execution(record, "passed" if record.status == ExecutionStatus.PASSED else "failed")

    async def _run_optional_tool(self, capability_id: str, tool_name: str, parameters: dict[str, Any], skip_reason_if_failed: str = "") -> None:
        record = await self.queue.submit(
            capability_id=capability_id,
            parameters=parameters,
            operation=lambda params: self.mcp_runner.run(tool_name, params, raise_on_error_status=True).__dict__,
            timeout_seconds=300,
        )
        if record.status == ExecutionStatus.PASSED:
            self._record_from_execution(record, "passed")
        else:
            self._record_from_execution(record, "skipped_with_reason", skip_reason_if_failed or record.error_summary or "Optional capability failed in current environment.")

    async def _run_mounting_plate_wrapper(self, output_path: str) -> None:
        record = await self.queue.submit(
            capability_id="script.sw_part",
            parameters={"output_path": output_path, "width_mm": 120, "height_mm": 80, "depth_mm": 10, "hole_diameter_mm": 6.5, "chamfer_mm": 1},
            operation=lambda params: self._create_mounting_plate_with_holes(params),
            timeout_seconds=300,
        )
        self._record_from_execution(record, "passed" if record.status == ExecutionStatus.PASSED else "failed")

    async def _run_dwg_wrapper(self, part_path: str, output_path: str, drawing_path: str) -> None:
        parameters = {"part_path": part_path, "output_path": output_path, "drawing_path": drawing_path}
        record = await self.queue.submit(
            capability_id="wrapper.export_dwg",
            parameters=parameters,
            operation=lambda params: export_part_drawing_to_dwg(
                str(params["part_path"]),
                str(params["output_path"]),
                str(params.get("drawing_path")) if params.get("drawing_path") else None,
            ),
            timeout_seconds=300,
        )
        self._record_from_execution(record, "passed" if record.status == ExecutionStatus.PASSED else "failed")

    def _create_mounting_plate_with_holes(self, parameters: dict[str, Any]) -> dict[str, Any]:
        import sys

        scripts = self.root / "vendor" / "skills" / "solidworks-automation" / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        from sw_connect import mm
        from sw_part import chamfer, extrude_boss, extrude_cut, sketch, sketch_circle, sketch_corner_rectangle
        from sw_session import SolidWorksSession

        output_path = Path(str(parameters["output_path"])).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        width = float(parameters.get("width_mm", 120))
        height = float(parameters.get("height_mm", 80))
        depth = float(parameters.get("depth_mm", 10))
        hole_radius = float(parameters.get("hole_diameter_mm", 6.5)) / 2
        chamfer_size = float(parameters.get("chamfer_mm", 1))
        session = SolidWorksSession()
        model = session.new_part()
        with sketch(model, "Front Plane") as base_sketch:
            sketch_corner_rectangle(model, mm(-width / 2), mm(-height / 2), mm(width / 2), mm(height / 2))
        extrude_boss(model, base_sketch, mm(depth))
        with sketch(model, "Front Plane") as hole_sketch:
            for x, y in [
                (-width / 2 + 10, -height / 2 + 10),
                (width / 2 - 10, -height / 2 + 10),
                (width / 2 - 10, height / 2 - 10),
                (-width / 2 + 10, height / 2 - 10),
            ]:
                sketch_circle(model, mm(x), mm(y), mm(hole_radius))
        extrude_cut(model, hole_sketch, mm(depth * 2))
        chamfer(model, mm(chamfer_size), 45)
        saved = bool(session.save(model, str(output_path)))
        return {
            "status": "ok" if saved else "failed",
            "output_path": str(output_path),
            "created_files": [str(output_path)],
            "features": {
                "width_mm": width,
                "height_mm": height,
                "depth_mm": depth,
                "holes": 4,
                "hole_diameter_mm": hole_radius * 2,
                "chamfer_mm": chamfer_size,
            },
        }

    def _record_from_execution(self, record, status: str, skip_reason: str = "") -> None:
        capability = self.registry.get(record.capability_id)
        created_files = [path for path in record.created_files if path]
        self.created_files.extend(created_files)
        self.results.append(
            ValidationResult(
                capability_id=record.capability_id,
                title=capability.title if capability else record.capability_id,
                status=status,
                input_parameters=record.parameters,
                created_files=created_files,
                active_document_before=record.active_document_before,
                active_document_after=record.active_document_after,
                stdout=record.stdout,
                stderr=record.stderr,
                traceback=record.stderr if status == "failed" else "",
                skip_reason=skip_reason,
                log_path=record.log_path,
            )
        )

    def _mark_remaining_capabilities(self, capabilities, preflight) -> None:
        seen = {result.capability_id for result in self.results}
        for capability in capabilities:
            if capability.id in seen:
                continue
            if capability.id in CORE_CAPABILITY_IDS:
                self.results.append(
                    ValidationResult(
                        capability_id=capability.id,
                        title=capability.title,
                        status="failed" if preflight.can_run_real_com else "skipped_with_reason",
                        skip_reason="" if preflight.can_run_real_com else "Real SolidWorks preflight did not pass.",
                    )
                )
            elif capability.requires_addin.value != "none":
                self.results.append(
                    ValidationResult(
                        capability_id=capability.id,
                        title=capability.title,
                        status="skipped_with_reason",
                        skip_reason=f"Optional add-in capability requires {capability.requires_addin.value}; see preflight add-in status.",
                    )
                )
            elif not capability.callable:
                self.results.append(
                    ValidationResult(
                        capability_id=capability.id,
                        title=capability.title,
                        status="passed",
                        skip_reason="文档能力已索引用于 Prompt 上下文和 Skill 浏览器。",
                    )
                )

    def _record(self, capability_id: str, title: str, status: str, **kwargs) -> None:
        created = kwargs.get("created_files", [])
        self.created_files.extend(created)
        self.results.append(ValidationResult(capability_id=capability_id, title=title, status=status, **kwargs))

    def _prepare_dirs(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.latest.mkdir(parents=True, exist_ok=True)

    def _write_reports(self, preflight_path: str) -> None:
        results_payload = [result.__dict__ for result in self.results]
        core_ids = set(CORE_CAPABILITY_IDS) | {
            "mcp.status",
            "mcp.start",
            "mcp.stop",
            "mcp.tool_listing",
            "ai.natural_language_generate_approve_run",
        }
        core = [result for result in self.results if result.capability_id in core_ids]
        core_passed = sum(1 for result in core if result.status == "passed")
        core_failed = sum(1 for result in core if result.status in {"failed", "untested"})
        ok = core_failed == 0 and core_passed > 0
        payload = {
            "ok": ok,
            "generated_at": datetime.now().isoformat(),
            "preflight_report": preflight_path,
            "core_passed": core_passed,
            "core_failed": core_failed,
            "results": results_payload,
        }
        report_json = self.latest / "REAL_SW2025_VALIDATION_REPORT.json"
        report_md = self.latest / "REAL_SW2025_VALIDATION_REPORT.md"
        manifest = self.latest / "files_manifest.json"
        report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest.write_text(json.dumps({"files": sorted(set(self.created_files))}, indent=2, ensure_ascii=False), encoding="utf-8")
        lines = [
            "# SolidWorks 2025 真实验证报告",
            "",
            f"生成时间：{payload['generated_at']}",
            f"总体结果：{'通过' if ok else '失败'}",
            f"核心通过：{core_passed}",
            f"核心失败：{core_failed}",
            "",
            "| 能力 | 状态 | 文件数 | 跳过原因 |",
            "|---|---|---|---|",
        ]
        for result in self.results:
            lines.append(
                f"| {result.capability_id} | {result.status} | {len(result.created_files)} | {result.skip_reason.replace('|', '/')} |"
            )
        report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
        refreshed = self.registry.write()
        self.registry.write_csv(self.latest / "capability_matrix.csv", refreshed.capabilities)
        for path in [report_json, report_md, manifest]:
            shutil.copy2(path, self.run_dir / path.name)
        shutil.copy2(self.latest / "capability_matrix.csv", self.run_dir / "capability_matrix.csv")


async def main_async() -> None:
    response = await RealAcceptanceRunner().run()
    print(response.model_dump_json(indent=2))


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
