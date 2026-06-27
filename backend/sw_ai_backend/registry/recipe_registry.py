from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Recipe:
    recipe_id: str
    capability_id: str
    title: str
    description: str
    parameters_schema: dict[str, Any]
    default_prompt: str
    mock_artifacts: list[str]
    maturity: str
    real_execution: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipe_id": self.recipe_id,
            "capability_id": self.capability_id,
            "title": self.title,
            "description": self.description,
            "parameters_schema": self.parameters_schema,
            "default_prompt": self.default_prompt,
            "mock_artifacts": self.mock_artifacts,
            "maturity": self.maturity,
            "real_execution": self.real_execution,
        }


class RecipeRegistry:
    def __init__(self) -> None:
        self._recipes = _build_recipes()

    def list(self) -> list[Recipe]:
        return list(self._recipes)

    def get(self, recipe_id: str) -> Recipe | None:
        return next((item for item in self._recipes if item.recipe_id == recipe_id), None)

    def for_capability(self, capability_id: str) -> list[Recipe]:
        return [item for item in self._recipes if item.capability_id == capability_id]

    def write(self) -> dict[str, Any]:
        recipes = [item.to_dict() for item in self._recipes]
        return {"generated_at": utc_now().isoformat(), "total": len(recipes), "recipes": recipes}


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or []}


def _recipe(
    recipe_id: str,
    capability_id: str,
    title: str,
    description: str,
    prompt: str,
    artifacts: list[str],
    *,
    maturity: str = "stable",
    real_execution: str = "requires_solidworks",
    schema: dict[str, Any] | None = None,
) -> Recipe:
    return Recipe(
        recipe_id=recipe_id,
        capability_id=capability_id,
        title=title,
        description=description,
        parameters_schema=schema or _schema({}),
        default_prompt=prompt,
        mock_artifacts=artifacts,
        maturity=maturity,
        real_execution=real_execution,
    )


def _build_recipes() -> list[Recipe]:
    part_schema = _schema(
        {
            "width_mm": {"type": "number", "default": 120},
            "height_mm": {"type": "number", "default": 80},
            "thickness_mm": {"type": "number", "default": 10},
            "hole_diameter_mm": {"type": "number", "default": 8},
        }
    )
    return [
        _recipe("basic_box", "ai.parametric_part_generator", "基础长方体", "创建可导出的基础长方体零件。", "生成 80 x 60 x 12 mm 基础长方体。", ["basic_box.SLDPRT.mock.txt", "parameters.json"], schema=part_schema),
        _recipe("cylinder", "ai.parametric_part_generator", "圆柱零件", "创建圆柱或轴套类基础零件。", "生成半径 20 mm、深度 80 mm 的圆柱。", ["cylinder.SLDPRT.mock.txt", "parameters.json"]),
        _recipe("mounting_plate", "ai.parametric_part_generator", "安装板", "四角孔安装板，是恢复验证的主 Recipe。", "生成 120 x 80 x 10 mm 四孔 mounting_plate，并导出 STEP 与复核报告。", ["mounting_plate.SLDPRT.mock.txt", "mounting_plate.STEP.mock.txt", "mounting_plate_parameters.json", "mounting_plate_review_report.json", "mounting_plate_review_summary.md"], schema=part_schema),
        _recipe("flange_plate", "ai.complex_mechanical_part_generator", "法兰板", "生成带中心孔与环形孔位的法兰板。", "生成法兰板，包含中心孔和 6 个安装孔。", ["flange_plate.SLDPRT.mock.txt", "parameters.json"], maturity="beta"),
        _recipe("l_bracket", "ai.complex_mechanical_part_generator", "L 型支架", "生成带孔 L 型机械支架。", "生成 L 型支架，包含底板与竖板安装孔。", ["l_bracket.SLDPRT.mock.txt", "review.json"], maturity="beta"),
        _recipe("shaft", "ai.shaft_revolved_part_generator", "阶梯轴", "生成轴类旋转件。", "生成两段式阶梯轴并导出 STEP。", ["shaft.SLDPRT.mock.txt", "shaft.STEP.mock.txt"], maturity="beta"),
        _recipe("cnc_mount", "ai.cnc_machined_part_generator", "CNC 安装座", "生成带倒角圆角的机加工安装座。", "生成 CNC mount，包含圆角、倒角和安装孔。", ["cnc_mount.SLDPRT.mock.txt", "review.json"], maturity="beta"),
        _recipe("threaded_hole_block", "ai.threaded_hole_engineering", "螺纹孔块", "生成包含螺纹孔参数记录的块体。", "生成 M6 螺纹孔块并输出孔参数。", ["threaded_hole_block.SLDPRT.mock.txt", "hole_report.json"], maturity="beta"),
        _recipe("basic_assembly", "ai.assembly_generator", "基础装配", "创建基础装配并加入两个组件。", "创建 shaft + rotor 基础装配。", ["basic_assembly.SLDASM.mock.txt", "component_report.json"], maturity="beta"),
        _recipe("motion_ready_fan", "ai.motion_ready_assembly_generator", "运动就绪风扇", "生成可进入 Motion Study 的风扇装配。", "生成 mini fan motion-ready assembly。", ["motion_ready_fan.SLDASM.mock.txt", "motion_setup.json"], maturity="experimental"),
        _recipe("three_view_drawing_pdf", "ai.drawing_bom_pdf_assistant", "三视图工程图 PDF", "从零件生成三视图工程图和 PDF。", "为当前零件生成三视图工程图并导出 PDF。", ["drawing.SLDDRW.mock.txt", "drawing.PDF.mock.txt"], maturity="beta"),
        _recipe("export_current_document", "ai.smart_export_batch_converter", "导出当前文档", "导出活动文档为 STEP/STL 等格式。", "导出当前文档为 STEP。", ["export_current_document.STEP.mock.txt"]),
        _recipe("batch_export", "ai.smart_export_batch_converter", "批量导出", "批量转换目录中的 SolidWorks 文件。", "批量导出目录中的零件为 STEP 和 STL。", ["batch_export_manifest.json"], maturity="beta"),
        _recipe("review_current_document", "ai.result_review_assistant", "复核当前文档", "读取当前模型状态并生成复核报告。", "复核当前活动文档并生成 JSON/Markdown 报告。", ["review_current_document.json", "review_current_document.md"]),
    ]

