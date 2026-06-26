from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from sw_ai_backend.core.paths import skill_paths, user_outputs_dir
from sw_ai_backend.solidworks.com_runtime import solidworks_com_runtime


def _ensure_vendor_scripts_on_path() -> None:
    scripts = skill_paths().solidworks_scripts
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))


def export_part_drawing_to_dwg(part_path: str = "", output_path: str = "", drawing_path: str | None = None) -> dict[str, Any]:
    """Create a drawing from a part and export that drawing to DWG using vendored SolidWorks helpers."""
    return export_part_drawing(part_path, output_path, drawing_path, export_format="dwg")


def export_part_drawing(
    part_path: str = "",
    output_path: str = "",
    drawing_path: str | None = None,
    export_format: str = "dwg",
) -> dict[str, Any]:
    """Create a drawing from a part and export that drawing to PDF, DXF, or DWG."""
    with solidworks_com_runtime(f"drawing export {export_format}"):
        _ensure_vendor_scripts_on_path()
        from sw_connect import connect_solidworks, get_com_member, new_document, save_document
        from sw_drawing import add_note, create_standard_views, insert_dimensions
        from sw_export import export_to_dxf, export_to_pdf

        sw, active = connect_solidworks(wait_seconds=1)
        if part_path:
            part = Path(part_path).expanduser().resolve()
        else:
            if active is None:
                raise RuntimeError("没有可用于 DWG 工程图导出的活动 SolidWorks 零件。")
            active_type = int(get_com_member(active, "GetType") or 0)
            if active_type != 1:
                raise RuntimeError("DWG wrapper 需要活动零件，或显式传入 .SLDPRT part_path。")
            active_path = str(get_com_member(active, "GetPathName") or "")
            if not active_path:
                raise RuntimeError("活动零件必须先保存，才能导出 DWG 工程图。")
            part = Path(active_path).expanduser().resolve()
        if not part.exists():
            raise FileNotFoundError(f"零件文件不存在：{part}")

        normalized_format = export_format.lower().lstrip(".")
        if normalized_format not in {"pdf", "dxf", "dwg"}:
            raise ValueError(f"Drawing wrapper 仅支持 pdf、dxf 或 dwg；收到 {export_format!r}。")

        defaults = default_validation_paths()
        output = Path(output_path or defaults["output_path"]).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.suffix.lower() != f".{normalized_format}":
            output = output.with_suffix(f".{normalized_format}")

        drawing = Path(drawing_path).expanduser().resolve() if drawing_path else output.with_suffix(".SLDDRW")
        drawing.parent.mkdir(parents=True, exist_ok=True)

        model = new_document(sw, "drawing")
        views_created = bool(create_standard_views(model, str(part)))
        dimension_error = ""
        try:
            dimensions_inserted = bool(insert_dimensions(model))
        except Exception as exc:
            dimensions_inserted = False
            dimension_error = str(exc)
        add_note(model, 0.08, 0.05, "SolidWorks AI Studio 验证 DWG 导出")
        saved_drawing = bool(save_document(model, str(drawing)))
        if normalized_format == "pdf":
            exported = bool(export_to_pdf(model, str(output)))
        else:
            exported = bool(export_to_dxf(model, str(output)))

        return {
            "status": "ok" if exported else "failed",
            "format": normalized_format,
            "part_path": str(part),
            "drawing_path": str(drawing),
            "output_path": str(output),
            "views_created": views_created,
            "dimensions_inserted": dimensions_inserted,
            "dimension_error": dimension_error,
            "saved_drawing": saved_drawing,
            "exported": exported,
            "document": {
                "title": get_com_member(model, "GetTitle"),
                "path": get_com_member(model, "GetPathName"),
                "type": get_com_member(model, "GetType"),
            },
        }


def default_validation_paths() -> dict[str, str]:
    out = user_outputs_dir() / "validation" / "latest" / "cad_samples" / "dwg_wrapper"
    return {
        "output_path": str(out / "acceptance_drawing_export.DWG"),
        "drawing_path": str(out / "acceptance_drawing_export.SLDDRW"),
    }
