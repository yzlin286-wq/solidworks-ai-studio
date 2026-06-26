from __future__ import annotations

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("SWAI_PROJECT_ROOT") or getattr(sys, "_MEIPASS", "") or Path.cwd())
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import os
import sys

# Import vendored SolidWorks automation helpers.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENDOR_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', '..', 'vendor', 'skills', 'solidworks-automation', 'scripts'))
if VENDOR_DIR not in sys.path:
    sys.path.insert(0, VENDOR_DIR)

from sw_session import SolidWorksSession
from sw_connect import mm
from sw_part import sketch, sketch_rectangle, sketch_circle, extrude_midplane, extrude_cut, chamfer

OUTPUT_DIR = r"C:\Users\Vision\Documents\sw skill 应用化\outputs\temp\generated\59e00ec72a1145cb86fed88e9bf1900f\outputs"
PART_PATH = os.path.join(OUTPUT_DIR, "m6_mounting_plate_120x80x10.SLDPRT")
STEP_PATH = os.path.join(OUTPUT_DIR, "m6_mounting_plate_120x80x10.STEP")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    session = SolidWorksSession()
    model = session.new_part()

    plate_length = mm(120)
    plate_width = mm(80)
    plate_thickness = mm(10)
    hole_diameter = mm(6.6)  # Standard M6 clearance through-hole.
    hole_offset_x = mm(10)
    hole_offset_y = mm(10)
    chamfer_size = mm(1)

    # Base plate: 120 x 80 mm, centered on the origin, 10 mm thick.
    with sketch(model, 'Front Plane') as base_sketch:
        sketch_rectangle(model, 0, 0, plate_length, plate_width)
    extrude_midplane(model, base_sketch, plate_thickness)

    # Four M6 clearance through holes near the corners.
    x = plate_length / 2.0 - hole_offset_x
    y = plate_width / 2.0 - hole_offset_y
    with sketch(model, 'Front Plane') as hole_sketch:
        sketch_circle(model, x, y, hole_diameter / 2.0)
        sketch_circle(model, -x, y, hole_diameter / 2.0)
        sketch_circle(model, -x, -y, hole_diameter / 2.0)
        sketch_circle(model, x, -y, hole_diameter / 2.0)
    extrude_cut(model, hole_sketch, 0)

    try:
        chamfer(model, chamfer_size)
    except Exception as exc:
        print('chamfer warning:', exc)

    session.save(model, PART_PATH)
    session.export(model, STEP_PATH)

    print('saved:', PART_PATH)
    print('exported:', STEP_PATH)


if __name__ == '__main__':
    main()