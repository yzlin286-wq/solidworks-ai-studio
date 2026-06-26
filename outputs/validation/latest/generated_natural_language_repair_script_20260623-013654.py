from __future__ import annotations

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
    output_dir = Path(r"C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples")
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
    print(report.get("evaluation", {}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
