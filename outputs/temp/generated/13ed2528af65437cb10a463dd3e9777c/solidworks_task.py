from __future__ import annotations

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("SWAI_PROJECT_ROOT") or getattr(sys, "_MEIPASS", "") or Path.cwd())
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import sys
from pathlib import Path

# Import only vendored SolidWorks automation helper modules.
SCRIPT_DIR = Path(__file__).resolve().parent
VENDORED = SCRIPT_DIR / "vendor" / "skills" / "solidworks-automation" / "scripts"
if not VENDORED.exists():
    # Common layout when this generated script is placed outside the repository root.
    for parent in SCRIPT_DIR.parents:
        candidate = parent / "vendor" / "skills" / "solidworks-automation" / "scripts"
        if candidate.exists():
            VENDORED = candidate
            break
sys.path.insert(0, str(VENDORED))

from sw_session import SolidWorksSession
from sw_connect import mm
from sw_part import sketch, sketch_rectangle, sketch_circle, extrude_midplane, extrude_cut, chamfer

OUTPUT_DIR = Path(r"C:\Users\Vision\Documents\sw skill 应用化\outputs\temp\generated\13ed2528af65437cb10a463dd3e9777c\outputs")
PART_PATH = OUTPUT_DIR / "m6_mounting_plate_120x80x10.SLDPRT"
STEP_PATH = OUTPUT_DIR / "m6_mounting_plate_120x80x10.STEP"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    session = SolidWorksSession()
    model = session.new_part()

    length = mm(120)
    width = mm(80)
    thickness = mm(10)
    hole_diameter = mm(6.6)  # Standard M6 normal clearance through-hole diameter.
    chamfer_size = mm(1)

    # Use a centered plate so hole locations are symmetric and stable.
    with sketch(model, "Front Plane") as base_sketch:
        sketch_rectangle(model, 0, 0, length, width)
    extrude_midplane(model, base_sketch, thickness)

    # Four M6 clearance through holes near the corners.
    edge_offset_x = mm(12)
    edge_offset_y = mm(12)
    x_positions = [-(length / 2) + edge_offset_x, (length / 2) - edge_offset_x]
    y_positions = [-(width / 2) + edge_offset_y, (width / 2) - edge_offset_y]

    with sketch(model, "Front Plane") as hole_sketch:
        for x in x_positions:
            for y in y_positions:
                sketch_circle(model, x, y, hole_diameter / 2)
    extrude_cut(model, hole_sketch, 0)

    try:
        chamfer(model, chamfer_size)
    except Exception as exc:
        print("chamfer warning:", exc)

    session.save(model, str(PART_PATH))
    session.export(model, str(STEP_PATH))
    print("saved part:", PART_PATH)
    print("exported step:", STEP_PATH)


if __name__ == "__main__":
    main()