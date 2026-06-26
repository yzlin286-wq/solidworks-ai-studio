from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("SWAI_PROJECT_ROOT") or getattr(sys, "_MEIPASS", "") or Path.cwd())
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

from sw_connect import mm
from sw_part import chamfer, extrude_boss, extrude_cut, sketch, sketch_circle, sketch_corner_rectangle
from sw_review import run_review
from sw_session import SolidWorksSession


def main() -> int:
    prompt = """新建一个 120 x 80 x 10 mm 安装板，四角各打 M6 通孔，倒角 1 mm，保存为 SLDPRT 并导出 STEP。"""
    output_dir = Path(r"C:\Users\Vision\Documents\sw skill 应用化\outputs\temp\generated\18d3cc80c043467baf478c641ba196e5\outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    part_path = output_dir / "ui_mounting_plate_120x80x10.SLDPRT"
    step_path = output_dir / "ui_mounting_plate_120x80x10.STEP"
    review_dir = output_dir / "ui_mounting_plate_review"

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
    if not session.save(model, str(part_path)):
        raise RuntimeError(f"Save failed: {part_path}")
    if not session.export(model, str(step_path)):
        raise RuntimeError(f"STEP export failed: {step_path}")
    report, report_path = run_review(
        model,
        review_dir,
        basename="ui_mounting_plate_120x80x10",
        expected_outputs=[str(part_path), str(step_path)],
    )
    print(f"Prompt: {prompt}")
    print(f"SLDPRT: {part_path}")
    print(f"STEP: {step_path}")
    print(f"Review: {report_path}")
    print(f"Review status: {report.get('evaluation', {})}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
