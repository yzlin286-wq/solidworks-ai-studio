from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AICapability:
    id: str
    title: str
    group: str
    status: str
    maturity: str
    ai_goal: str
    user_intents: list[str]
    execution_modes: list[str]
    requires: list[str]
    source_files: list[str]
    default_outputs: list[str]
    approval_required: bool = True
    source_missing: bool = False
    not_primary_entries: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "group": self.group,
            "status": self.status,
            "maturity": self.maturity,
            "ai_goal": self.ai_goal,
            "user_intents": self.user_intents,
            "execution_modes": self.execution_modes,
            "requires": self.requires,
            "source_files": self.source_files,
            "default_outputs": self.default_outputs,
            "approval_required": self.approval_required,
            "source_missing": self.source_missing,
            "not_primary_entries": self.not_primary_entries,
        }


class AICapabilityRegistry:
    def __init__(self) -> None:
        self._capabilities = _build_capabilities()

    def list(self) -> list[AICapability]:
        return list(self._capabilities)

    def get(self, capability_id: str) -> AICapability | None:
        return next((item for item in self._capabilities if item.id == capability_id), None)

    def groups(self) -> dict[str, list[AICapability]]:
        grouped: dict[str, list[AICapability]] = {}
        for capability in self._capabilities:
            grouped.setdefault(capability.group, []).append(capability)
        return grouped

    def write(self) -> dict[str, Any]:
        capabilities = [item.to_dict() for item in self._capabilities]
        groups = [
            {"name": group, "count": len(items), "capability_ids": [item.id for item in items]}
            for group, items in self.groups().items()
        ]
        return {
            "generated_at": utc_now().isoformat(),
            "total": len(capabilities),
            "groups": groups,
            "capabilities": capabilities,
        }


def _cap(
    id: str,
    title: str,
    group: str,
    status: str,
    maturity: str,
    goal: str,
    intents: list[str],
    modes: list[str],
    requires: list[str],
    sources: list[str],
    outputs: list[str],
    *,
    source_missing: bool = False,
) -> AICapability:
    return AICapability(
        id=id,
        title=title,
        group=group,
        status=status,
        maturity=maturity,
        ai_goal=goal,
        user_intents=intents,
        execution_modes=modes,
        requires=requires,
        source_files=sources,
        default_outputs=outputs,
        source_missing=source_missing,
    )


def _build_capabilities() -> list[AICapability]:
    return [
        _cap("ai.environment_preflight", "环境预检", "System", "Ready Tool", "stable", "诊断本地后端、LLM Provider、SolidWorks COM 与模板路径。", ["健康检查", "确认可执行性"], ["read_only"], ["backend"], ["scripts/sw2025_preflight.ps1"], ["preflight JSON", "preflight Markdown"]),
        _cap("ai.cad_task_studio", "CAD 任务工作台", "AI CAD Studio", "Ready Tool / AI Script", "stable", "承载自然语言到可审批任务的完整链路。", ["自然语言建模", "任务审批"], ["mock", "real"], ["LLM", "approval"], ["backend/sw_ai_backend/api/ai_capabilities.py"], ["task record", "artifacts"]),
        _cap("ai.parametric_part_generator", "参数化零件生成", "Part & Manufacturing", "Recipe / AI Script", "stable", "生成基础参数化零件与 mounting_plate 等模板。", ["创建安装板", "创建基础零件"], ["mock", "real"], ["SolidWorks COM", "approval"], ["vendor/skills/solidworks-automation/scripts/sw_part.py"], ["SLDPRT", "STEP", "parameters JSON", "review"]),
        _cap("ai.complex_mechanical_part_generator", "复杂机械零件生成", "Part & Manufacturing", "Recipe / AI Script", "beta", "组合草图、拉伸、切除、圆角等特征。", ["复杂零件", "多特征零件"], ["mock", "real"], ["SolidWorks COM", "approval"], ["vendor/skills/solidworks-automation/examples/02_complex_part.py"], ["SLDPRT", "STEP"]),
        _cap("ai.cnc_machined_part_generator", "CNC 机加工零件", "Part & Manufacturing", "Recipe", "beta", "生成更接近机加工的倒角、圆角与安装孔结构。", ["CNC 支架", "机加工设计"], ["mock", "real"], ["SolidWorks COM", "approval"], ["vendor/skills/solidworks-automation/subskills/solidworks-fillet-chamfer-cnc"], ["SLDPRT", "review"]),
        _cap("ai.threaded_hole_engineering", "螺纹孔工程", "Part & Manufacturing", "Recipe / AI Script", "beta", "按工程参数创建螺纹孔相关结构。", ["螺纹孔", "孔位阵列"], ["mock", "real"], ["SolidWorks COM", "approval"], ["vendor/skills/solidworks-automation/subskills/solidworks-threaded-holes"], ["SLDPRT", "hole report"]),
        _cap("ai.shaft_revolved_part_generator", "轴类旋转件", "Part & Manufacturing", "Recipe", "beta", "创建轴类、圆柱类与旋转体零件。", ["轴", "圆柱件"], ["mock", "real"], ["SolidWorks COM", "approval"], ["vendor/skills/solidworks-automation/scripts/sw_part.py"], ["SLDPRT", "STEP"]),
        _cap("ai.existing_model_modifier", "现有模型修改", "Part & Manufacturing", "AI Script", "beta", "打开已有模型并执行可审计的参数修改。", ["修改现有零件", "批量调整"], ["real"], ["active document", "approval"], ["vendor/skills/solidworks-automation/scripts/sw_part.py"], ["modified SLDPRT", "change report"]),
        _cap("ai.assembly_generator", "装配生成", "Assembly & Motion", "Ready Tool / AI Script", "stable", "创建装配并添加零部件。", ["生成装配", "添加组件"], ["mock", "real"], ["SolidWorks COM", "approval"], ["vendor/skills/solidworks-automation/scripts/sw_assembly.py"], ["SLDASM", "component report"]),
        _cap("ai.mechanical_mate_dof_assistant", "机械配合与自由度助手", "Assembly & Motion", "Ready Tool / Requires Add-in", "beta", "添加同心、重合、距离等配合并说明自由度。", ["添加配合", "检查自由度"], ["real"], ["SolidWorks COM", "assembly"], ["vendor/skills/solidworks-automation/scripts/sw_assembly.py"], ["mate report"]),
        _cap("ai.motion_ready_assembly_generator", "运动就绪装配", "Assembly & Motion", "Recipe / Experimental", "beta", "创建可进入运动分析的装配结构。", ["风扇装配", "运动准备"], ["mock", "real"], ["SolidWorks COM", "motion add-in optional"], ["vendor/skills/solidworks-automation/examples/08_mini_fan_motion_assembly.py"], ["SLDASM", "motion setup"]),
        _cap("ai.motion_study_assistant", "Motion Study 助手", "Assembly & Motion", "Requires Add-in / Docs Only", "experimental", "辅助配置旋转马达与运动算例。", ["运动分析", "旋转马达"], ["real"], ["Motion add-in"], ["vendor/skills/solidworks-automation/scripts/sw_motion.py"], ["motion report"], source_missing=False),
        _cap("ai.drawing_bom_pdf_assistant", "工程图 BOM PDF 助手", "Drawing & Output", "Ready Tool / AI Script", "stable", "从零件或装配创建工程图并导出 PDF。", ["工程图", "PDF", "BOM"], ["mock", "real"], ["SolidWorks COM", "drawing template"], ["vendor/skills/solidworks-automation/scripts/sw_drawing.py"], ["SLDDRW", "PDF"]),
        _cap("ai.smart_export_batch_converter", "智能导出与批量转换", "Drawing & Output", "Ready Tool / Utility", "stable", "导出 STEP/STL/IGES/PDF/DXF/DWG 等格式。", ["格式转换", "批量导出"], ["mock", "real"], ["SolidWorks COM"], ["vendor/skills/solidworks-automation/scripts/sw_export.py"], ["STEP", "STL", "PDF", "DXF", "DWG"]),
        _cap("ai.appearance_material_coloring", "外观材质与颜色", "Drawing & Output", "Ready Tool", "stable", "设置模型颜色、材质和外观。", ["颜色", "外观"], ["real"], ["SolidWorks COM", "active document"], ["vendor/skills/solidworks-automation/scripts/sw_appearance.py"], ["appearance report"]),
        _cap("ai.result_review_assistant", "结果复核助手", "Review & Repair", "Ready Tool", "stable", "读取活动文档与导出产物，生成复核报告。", ["复核模型", "生成报告"], ["mock", "real"], ["active document optional"], ["vendor/skills/solidworks-automation/scripts/sw_review.py"], ["review JSON", "review Markdown", "preview images"]),
        _cap("ai.model_repair_assistant", "模型修复助手", "Review & Repair", "AI Script", "beta", "针对失败执行和模型问题提供修复建议。", ["修复错误", "诊断失败"], ["mock", "real"], ["task evidence"], ["vendor/skills/solidworks-automation/references/troubleshooting.md"], ["repair plan"]),
        _cap("ai.sheet_metal_assistant", "Sheet Metal 助手", "Engineering Data", "Requires Add-in / Docs Only", "experimental", "提供 Sheet Metal 建模路径和脚本提示。", ["钣金", "展开"], ["docs"], ["Sheet Metal"], ["vendor/skills/solidworks-automation/references/advanced.md"], ["implementation plan"], source_missing=True),
        _cap("ai.weldment_structure_assistant", "Weldment 结构助手", "Engineering Data", "Requires Add-in / Docs Only", "experimental", "提供 Weldment 结构建模路径和脚本提示。", ["焊件", "型材结构"], ["docs"], ["Weldments"], ["vendor/skills/solidworks-automation/references/advanced.md"], ["implementation plan"], source_missing=True),
        _cap("ai.surface_advanced_geometry_assistant", "曲面与高级几何助手", "Engineering Data", "Docs Only / AI Script", "experimental", "为曲面和高级几何任务生成受控计划。", ["曲面", "复杂几何"], ["docs", "real"], ["advanced modeling"], ["vendor/skills/solidworks-automation/references/advanced.md"], ["plan", "script draft"]),
        _cap("ai.properties_config_design_table", "属性、配置与 Design Table", "Engineering Data", "AI Script", "beta", "管理自定义属性、配置和设计表相关任务。", ["自定义属性", "配置"], ["mock", "real"], ["SolidWorks COM"], ["vendor/skills/solidworks-automation/references/api-lookup.md"], ["property report"]),
        _cap("ai.fea_simulation_assistant", "FEA Simulation 助手", "Engineering Data", "Requires Add-in / Docs Only", "experimental", "提供 Simulation 前处理与验证路径。", ["仿真", "FEA"], ["docs"], ["Simulation add-in"], ["vendor/skills/solidworks-automation/references/advanced.md"], ["simulation checklist"], source_missing=True),
        _cap("ai.vba_macro_guard", "VBA Macro Guard", "Integration", "Ready Tool / Utility", "stable", "审查宏和脚本中的高风险调用。", ["宏安全", "静态检查"], ["mock", "real"], ["script"], ["vendor/skills/solidworks-automation/scripts/sw_macro_guard.py"], ["guard report"]),
        _cap("ai.api_lookup_and_capability_builder", "API Lookup 与 Capability Builder", "Integration", "Docs Only / Core Extension", "beta", "定位 API、能力文件和扩展边界。", ["查 API", "扩展能力"], ["docs"], ["skill docs"], ["vendor/skills/solidworks-automation/references/api-lookup.md"], ["lookup report"]),
        _cap("ai.mcp_integration_assistant", "MCP 集成助手", "Integration", "Ready Tool", "stable", "管理 MCP server、工具清单与连接片段。", ["MCP", "工具调用"], ["read_only", "real"], ["MCP"], ["vendor/skills/solidworks-automation/mcp-server/server.py"], ["MCP tool list"]),
        _cap("ai.example_template_center", "示例模板中心", "Knowledge & Troubleshooting", "Ready / Recipe Seed", "stable", "展示和复用内置示例、Recipe 种子。", ["示例", "模板"], ["mock"], ["recipe registry"], ["vendor/skills/solidworks-automation/examples"], ["recipe list"]),
        _cap("ai.troubleshooting_diagnosis", "故障诊断", "Knowledge & Troubleshooting", "Docs Only / AI Script", "stable", "根据错误、日志和预检输出给出诊断路径。", ["排障", "失败分析"], ["mock", "real"], ["logs"], ["vendor/skills/solidworks-automation/references/troubleshooting.md"], ["diagnosis report"]),
    ]

