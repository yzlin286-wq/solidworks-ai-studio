from __future__ import annotations

import ast
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sw_ai_backend.core.paths import project_root, skill_paths, validation_latest_dir
from sw_ai_backend.models.schemas import (
    AddinRequirement,
    Capability,
    CapabilityExecutionKind,
    CapabilityListResponse,
    CapabilitySourceType,
    RealValidationStatus,
)


CAPABILITIES_PATH = project_root() / "backend" / "generated" / "solidworks_skill_capabilities.json"


TITLE_TRANSLATIONS = {
    "01_basic_part": "示例：基础零件",
    "02_complex_part": "示例：复杂零件",
    "03_assembly": "示例：装配体",
    "04_batch_export": "示例：批量导出",
    "05_drawing": "示例：工程图",
    "06_friendly_api": "示例：Friendly API",
    "07_motion_study_rotary_motor": "示例：Motion Study 旋转马达",
    "08_mini_fan_motion_assembly": "示例：迷你风扇运动装配体",
    "export_dwg": "导出 DWG",
    "solidworks_add_coincident_mate": "添加 Coincident Mate",
    "solidworks_add_component": "添加组件",
    "solidworks_add_concentric_mate": "添加 Concentric Mate",
    "solidworks_add_distance_mate": "添加 Distance Mate",
    "solidworks_add_rotary_motor": "添加 Rotary Motor",
    "solidworks_close_documents": "关闭文档",
    "solidworks_connect": "连接 SolidWorks",
    "solidworks_create_basic_part": "创建基础零件",
    "solidworks_export_active": "导出活动文档",
    "solidworks_health_check": "健康检查",
    "solidworks_new_document": "新建文档",
    "solidworks_open_document": "打开文档",
    "solidworks_review_active": "审查活动文档",
    "solidworks_save_document": "保存文档",
    "solidworks_set_appearance": "设置外观",
    "solidworks_set_component_fixed": "固定组件",
    "sw_appearance": "外观脚本",
    "sw_assembly": "装配体脚本",
    "sw_connect": "连接脚本",
    "sw_drawing": "工程图脚本",
    "sw_export": "导出脚本",
    "sw_macro_guard": "Macro Guard 脚本",
    "sw_motion": "Motion 脚本",
    "sw_part": "零件脚本",
    "sw_preflight": "Preflight 自检脚本",
    "sw_review": "审查脚本",
    "sw_session": "会话脚本",
    "validate_mcp": "验证 MCP",
    "validate_skill": "验证 Skill",
}

MARKDOWN_TITLE_TRANSLATIONS = {
    "SolidWorks automation skill instructions": "SolidWorks automation Skill 指令",
    "SolidWorks Fillet Chamfer CNC": "SolidWorks CNC 圆角/倒角",
    "SolidWorks Threaded Holes": "SolidWorks 螺纹孔",
}


CORE_CAPABILITY_IDS = {
    "mcp.solidworks_connect",
    "mcp.solidworks_health_check",
    "mcp.solidworks_new_document",
    "mcp.solidworks_create_basic_part",
    "mcp.solidworks_open_document",
    "mcp.solidworks_save_document",
    "mcp.solidworks_export_active",
    "mcp.solidworks_review_active",
    "mcp.solidworks_add_component",
    "mcp.solidworks_add_coincident_mate",
    "mcp.solidworks_add_distance_mate",
    "mcp.solidworks_add_concentric_mate",
    "mcp.solidworks_set_appearance",
}


class CapabilityRegistry:
    def __init__(self) -> None:
        self.paths = skill_paths()

    def build(self, merge_validation: bool = True) -> CapabilityListResponse:
        capabilities: list[Capability] = []
        capabilities.extend(self._skill_md_capabilities())
        capabilities.extend(self._script_capabilities())
        capabilities.extend(self._mcp_capabilities())
        capabilities.extend(self._wrapper_capabilities())
        capabilities.extend(self._markdown_capabilities("references", CapabilitySourceType.REFERENCE, False))
        capabilities.extend(self._markdown_capabilities("subskills", CapabilitySourceType.SUBSKILL, True))
        capabilities.extend(self._example_capabilities())
        capabilities = self._dedupe(capabilities)
        if merge_validation:
            capabilities = self._merge_validation(capabilities)
        return CapabilityListResponse(
            capabilities_path=str(CAPABILITIES_PATH),
            capabilities=sorted(capabilities, key=lambda item: (item.source_type.value, item.id)),
        )

    def write(self) -> CapabilityListResponse:
        response = self.build()
        CAPABILITIES_PATH.parent.mkdir(parents=True, exist_ok=True)
        CAPABILITIES_PATH.write_text(response.model_dump_json(indent=2), encoding="utf-8")
        return response

    def get(self, capability_id: str) -> Capability | None:
        for capability in self.build().capabilities:
            if capability.id == capability_id:
                return capability
        return None

    def write_csv(self, path: Path, capabilities: list[Capability] | None = None) -> None:
        rows = capabilities or self.build().capabilities
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "id",
                    "title",
                    "source_type",
                    "callable",
                    "execution_kind",
                    "requires_solidworks",
                    "requires_active_document",
                    "requires_part",
                    "requires_assembly",
                    "requires_drawing",
                    "requires_addin",
                    "ui_exposed",
                    "api_endpoint",
                    "real_sw2025_status",
                    "skip_reason",
                    "source_path",
                ],
            )
            writer.writeheader()
            for capability in rows:
                writer.writerow(
                    {
                        "id": capability.id,
                        "title": capability.title,
                        "source_type": capability.source_type.value,
                        "callable": capability.callable,
                        "execution_kind": capability.execution_kind.value,
                        "requires_solidworks": capability.requires_solidworks,
                        "requires_active_document": capability.requires_active_document,
                        "requires_part": capability.requires_part,
                        "requires_assembly": capability.requires_assembly,
                        "requires_drawing": capability.requires_drawing,
                        "requires_addin": capability.requires_addin.value,
                        "ui_exposed": capability.ui_exposed,
                        "api_endpoint": capability.api_endpoint,
                        "real_sw2025_status": capability.real_sw2025_status.value,
                        "skip_reason": capability.skip_reason,
                        "source_path": capability.source_path,
                    }
                )

    def _skill_md_capabilities(self) -> list[Capability]:
        path = self.paths.solidworks / "SKILL.md"
        if not path.exists():
            return []
        return [
                self._capability(
                    capability_id="skill.solidworks-automation",
                    title="SolidWorks automation Skill 指令",
                source_type=CapabilitySourceType.SKILL_MD,
                source_path=path,
                callable=False,
                execution_kind=CapabilityExecutionKind.PROMPT_CONTEXT,
                requires_solidworks=False,
                test_case="Included in AI planning context and Skill Browser.",
            )
        ]

    def _script_capabilities(self) -> list[Capability]:
        scripts = self.paths.solidworks_scripts
        if not scripts.exists():
            return []
        capabilities: list[Capability] = []
        for path in sorted(scripts.glob("*.py")):
            if path.name == "__init__.py":
                continue
            stem = path.stem
            public_functions = self._public_functions(path)
            capabilities.append(
                self._capability(
                    capability_id=f"script.{stem}",
                    title=self._title_from_name(stem),
                    source_type=CapabilitySourceType.SCRIPT,
                    source_path=path,
                    callable=True,
                    execution_kind=CapabilityExecutionKind.PYTHON_SCRIPT,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "script": {"type": "string", "description": f"Wrapper execution for {path.name}."},
                            "functions": {"type": "array", "items": {"type": "string"}, "default": public_functions},
                        },
                    },
                    output_schema={"type": "object", "properties": {"stdout": {"type": "string"}, "created_files": {"type": "array"}}},
                    requires_solidworks=self._requires_solidworks(stem),
                    requires_active_document=self._requires_active_doc(stem),
                    requires_part=self._requires_part(stem),
                    requires_assembly=self._requires_assembly(stem),
                    requires_drawing=self._requires_drawing(stem),
                    requires_addin=self._addin_requirement(stem),
                    test_case=f"Import {stem} and execute its acceptance wrapper or public functions through a real SolidWorks session.",
                )
            )
        return capabilities

    def _mcp_capabilities(self) -> list[Capability]:
        server = self.paths.solidworks_mcp_server
        if not server.exists():
            return []
        try:
            module = ast.parse(server.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            return []
        class_schemas = self._pydantic_model_schemas(module)
        tools: list[Capability] = []
        for node in module.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            if not self._is_mcp_tool(node):
                continue
            description = self._decorator_description(node) or ast.get_docstring(node) or self._title_from_name(node.name)
            annotation = node.args.args[0].annotation if node.args.args and node.args.args[0].arg == "params" else None
            model_name = ast.unparse(annotation) if annotation else ""
            tools.append(
                self._capability(
                    capability_id=f"mcp.{node.name}",
                    title=self._title_from_name(node.name),
                    source_type=CapabilitySourceType.MCP_TOOL,
                    source_path=server,
                    callable=True,
                    execution_kind=CapabilityExecutionKind.MCP_TOOL,
                    input_schema=class_schemas.get(model_name, {"type": "object", "properties": {}}),
                    output_schema={"type": "string", "description": description},
                    requires_solidworks=node.name not in {"solidworks_health_check"},
                    requires_active_document=self._requires_active_doc(node.name),
                    requires_part=self._requires_part(node.name),
                    requires_assembly=self._requires_assembly(node.name),
                    requires_drawing=self._requires_drawing(node.name),
                    requires_addin=self._addin_requirement(node.name),
                    test_case=f"Call upstream MCP tool {node.name} through serialized backend execution.",
                )
            )
        return tools

    def _wrapper_capabilities(self) -> list[Capability]:
        path = project_root() / "backend" / "sw_ai_backend" / "solidworks" / "dwg_export.py"
        return [
            self._capability(
                capability_id="wrapper.export_dwg",
                title="导出 DWG",
                source_type=CapabilitySourceType.SCRIPT,
                source_path=path,
                callable=True,
                execution_kind=CapabilityExecutionKind.PYTHON_SCRIPT,
                input_schema={
                    "type": "object",
                    "properties": {
                        "part_path": {"type": "string", "description": "Absolute .SLDPRT path used to create the drawing."},
                        "output_path": {"type": "string", "description": "Absolute .DWG output path."},
                        "drawing_path": {"type": "string", "description": "Optional .SLDDRW path."},
                    },
                    "required": ["part_path", "output_path"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "drawing_path": {"type": "string"},
                        "output_path": {"type": "string"},
                        "exported": {"type": "boolean"},
                    },
                },
                requires_solidworks=True,
                requires_active_document=False,
                requires_part=True,
                requires_drawing=True,
                test_case="Create a drawing from a real part and export the drawing to DWG through SolidWorks SaveAs.",
            )
        ]

    def _markdown_capabilities(self, folder: str, source_type: CapabilitySourceType, callable_default: bool) -> list[Capability]:
        root = self.paths.solidworks / folder
        if not root.exists():
            return []
        caps: list[Capability] = []
        for path in sorted(root.rglob("*.md")):
            rel = path.relative_to(self.paths.solidworks).as_posix()
            text = path.read_text(encoding="utf-8", errors="replace")
            title = self._markdown_title(path, text)
            stem = re.sub(r"[^a-z0-9]+", "-", rel.lower()).strip("-")
            callable_capability = callable_default and "scripts/" in text
            caps.append(
                self._capability(
                    capability_id=f"{source_type.value}.{stem}",
                    title=title,
                    source_type=source_type,
                    source_path=path,
                    callable=callable_capability,
                    execution_kind=CapabilityExecutionKind.PROMPT_CONTEXT if callable_capability else CapabilityExecutionKind.DOCUMENTATION_ONLY,
                    requires_solidworks=callable_capability,
                    requires_active_document=self._requires_active_doc(rel),
                    requires_part=self._requires_part(rel),
                    requires_assembly=self._requires_assembly(rel),
                    requires_drawing=self._requires_drawing(rel),
                    requires_addin=self._addin_requirement(rel),
                    test_case=f"Read {rel} into context; execute linked script when present.",
                )
            )
        return caps

    def _example_capabilities(self) -> list[Capability]:
        root = self.paths.solidworks / "examples"
        if not root.exists():
            return []
        caps: list[Capability] = []
        for path in sorted(root.glob("*.py")):
            stem = path.stem
            caps.append(
                self._capability(
                    capability_id=f"example.{stem}",
                    title=self._title_from_name(stem),
                    source_type=CapabilitySourceType.EXAMPLE,
                    source_path=path,
                    callable=True,
                    execution_kind=CapabilityExecutionKind.PYTHON_SCRIPT,
                    input_schema={"type": "object", "properties": {"output_dir": {"type": "string"}}},
                    output_schema={"type": "object", "properties": {"created_files": {"type": "array"}}},
                    requires_solidworks=True,
                    requires_active_document=False,
                    requires_part="part" in stem,
                    requires_assembly="assembly" in stem or "fan" in stem,
                    requires_drawing="drawing" in stem,
                    requires_addin=self._addin_requirement(stem),
                    test_case=f"Run example script {path.name} against SolidWorks 2025 in validation output directory.",
                )
            )
        return caps

    def _capability(
        self,
        capability_id: str,
        title: str,
        source_type: CapabilitySourceType,
        source_path: Path,
        callable: bool,
        execution_kind: CapabilityExecutionKind,
        requires_solidworks: bool,
        test_case: str,
        input_schema: dict[str, Any] | None = None,
        output_schema: dict[str, Any] | None = None,
        requires_active_document: bool = False,
        requires_part: bool = False,
        requires_assembly: bool = False,
        requires_drawing: bool = False,
        requires_addin: AddinRequirement = AddinRequirement.NONE,
    ) -> Capability:
        return Capability(
            id=capability_id,
            title=title,
            source_type=source_type,
            source_path=str(source_path),
            callable=callable,
            execution_kind=execution_kind,
            input_schema=input_schema or {"type": "object", "properties": {}},
            output_schema=output_schema or {"type": "object", "properties": {}},
            requires_solidworks=requires_solidworks,
            requires_active_document=requires_active_document,
            requires_part=requires_part,
            requires_assembly=requires_assembly,
            requires_drawing=requires_drawing,
            requires_addin=requires_addin,
            ui_exposed=True,
            api_endpoint=f"/api/skills/capabilities/{capability_id}/run" if callable else "",
            test_case=test_case,
        )

    def _dedupe(self, capabilities: list[Capability]) -> list[Capability]:
        seen: dict[str, Capability] = {}
        for capability in capabilities:
            seen[capability.id] = capability
        return list(seen.values())

    def _merge_validation(self, capabilities: list[Capability]) -> list[Capability]:
        report = validation_latest_dir() / "REAL_SW2025_VALIDATION_REPORT.json"
        if not report.exists():
            return capabilities
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return capabilities
        results = {item.get("capability_id"): item for item in data.get("results", []) if item.get("capability_id")}
        merged: list[Capability] = []
        for capability in capabilities:
            result = results.get(capability.id)
            if result:
                status_value = result.get("status", "untested")
                try:
                    status = RealValidationStatus(status_value)
                except ValueError:
                    status = RealValidationStatus.UNTESTED
                merged.append(
                    capability.model_copy(
                        update={
                            "real_sw2025_status": status,
                            "skip_reason": str(result.get("skip_reason", "")),
                        }
                    )
                )
            else:
                merged.append(capability)
        return merged

    def _pydantic_model_schemas(self, module: ast.Module) -> dict[str, dict[str, Any]]:
        schemas: dict[str, dict[str, Any]] = {}
        for node in module.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if not any(getattr(base, "id", "") == "BaseModel" or getattr(base, "attr", "") == "BaseModel" for base in node.bases):
                continue
            properties: dict[str, Any] = {}
            required: list[str] = []
            for stmt in node.body:
                target_name = ""
                annotation = None
                value = None
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    target_name = stmt.target.id
                    annotation = stmt.annotation
                    value = stmt.value
                if not target_name:
                    continue
                properties[target_name] = self._annotation_schema(annotation)
                if value is None:
                    required.append(target_name)
            schemas[node.name] = {"type": "object", "properties": properties, "required": required}
        return schemas

    def _annotation_schema(self, annotation: ast.AST | None) -> dict[str, Any]:
        if annotation is None:
            return {"type": "string"}
        text = ast.unparse(annotation)
        if "float" in text:
            return {"type": "number"}
        if "int" in text:
            return {"type": "integer"}
        if "bool" in text:
            return {"type": "boolean"}
        if "list" in text.lower() or "List" in text:
            return {"type": "array"}
        return {"type": "string"}

    def _public_functions(self, path: Path) -> list[str]:
        try:
            module = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            return []
        return [node.name for node in module.body if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")]

    def _is_mcp_tool(self, node: ast.FunctionDef) -> bool:
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "tool":
                return True
        return False

    def _decorator_description(self, node: ast.FunctionDef) -> str:
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            for keyword in decorator.keywords:
                if keyword.arg == "description" and isinstance(keyword.value, ast.Constant):
                    return str(keyword.value.value)
            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                return str(decorator.args[0].value)
        return ""

    def _markdown_title(self, path: Path, text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return self._localize_markdown_title(stripped.lstrip("#").strip())
        return self._title_from_name(path.stem)

    def _title_from_name(self, name: str) -> str:
        translated = TITLE_TRANSLATIONS.get(name.lower())
        if translated:
            return translated
        text = re.sub(r"^\d+[_-]*", "", name)
        return text.replace("_", " ").replace("-", " ").strip().title()

    def _localize_markdown_title(self, title: str) -> str:
        return MARKDOWN_TITLE_TRANSLATIONS.get(title, title)

    def _requires_solidworks(self, name: str) -> bool:
        lowered = name.lower()
        return not any(token in lowered for token in ["validate_skill"])

    def _requires_active_doc(self, name: str) -> bool:
        lowered = name.lower()
        return any(token in lowered for token in ["export", "review", "save", "appearance", "mate", "component", "motion", "drawing"])

    def _requires_part(self, name: str) -> bool:
        lowered = name.lower()
        return any(token in lowered for token in ["part", "appearance", "export", "review"]) and "assembly" not in lowered

    def _requires_assembly(self, name: str) -> bool:
        lowered = name.lower()
        return any(token in lowered for token in ["assembly", "component", "mate", "concentric", "coincident", "distance", "motor", "motion", "fan"])

    def _requires_drawing(self, name: str) -> bool:
        return "drawing" in name.lower() or "pdf" in name.lower() or "dxf" in name.lower() or "dwg" in name.lower()

    def _addin_requirement(self, name: str) -> AddinRequirement:
        lowered = name.lower()
        if any(token in lowered for token in ["motion", "motor"]):
            return AddinRequirement.MOTION
        if any(token in lowered for token in ["simulation", "fea"]):
            return AddinRequirement.SIMULATION
        if "sheet" in lowered or "metal" in lowered:
            return AddinRequirement.SHEET_METAL
        if "weld" in lowered:
            return AddinRequirement.WELDMENTS
        return AddinRequirement.NONE


def generate_capabilities_file() -> CapabilityListResponse:
    return CapabilityRegistry().write()


def main() -> None:
    response = generate_capabilities_file()
    print(response.capabilities_path)
    print(f"{len(response.capabilities)} capabilities indexed at {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
