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

# Human review gate: this script must be reviewed and approved before execution.
APPROVED_BY_HUMAN = False
if not APPROVED_BY_HUMAN:
    raise RuntimeError("Execution blocked: set APPROVED_BY_HUMAN = True only after human review and approval.")

VENDORED_SCRIPTS = Path(__file__).resolve().parents[1] / "vendor" / "skills" / "solidworks-automation" / "scripts"
if not VENDORED_SCRIPTS.exists():
    # Fallback for common execution from repository root or generated-script directories.
    candidate = Path.cwd() / "vendor" / "skills" / "solidworks-automation" / "scripts"
    if candidate.exists():
        VENDORED_SCRIPTS = candidate

if str(VENDORED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SCRIPTS))

from sw_session import SolidWorksSession
from sw_connect import mm
from sw_part import sketch, sketch_rectangle, sketch_circle, extrude_midplane, extrude_cut, chamfer

OUTPUT_DIR = Path(r"C:\Users\Vision\Documents\sw skill 应用化\outputs\temp\generated\9fe3d4ca32f740a698733d6a9572a9ae\outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

part_path = OUTPUT_DIR / "m6_mounting_plate_120x80x10.SLDPRT"
step_path = OUTPUT_DIR / "m6_mounting_plate_120x80x10.STEP"

# Plate dimensions
plate_length = mm(120)
plate_width = mm(80)
plate_thickness = mm(10)

# M6 normal clearance through-hole diameter
hole_diameter = mm(6.6)
hole_radius = hole_diameter / 2.0

# Hole centers inset from each edge. This is a practical default for an M6 mounting plate.
hole_inset_x = mm(15)
hole_inset_y = mm(15)

hole_centers = [
    (-plate_length / 2.0 + hole_inset_x, -plate_width / 2.0 + hole_inset_y),
    ( plate_length / 2.0 - hole_inset_x, -plate_width / 2.0 + hole_inset_y),
    ( plate_length / 2.0 - hole_inset_x,  plate_width / 2.0 - hole_inset_y),
    (-plate_length / 2.0 + hole_inset_x,  plate_width / 2.0 - hole_inset_y),
]

session = SolidWorksSession()
model = session.new_part()

with sketch(model, "Front Plane") as base_sketch:
    sketch_rectangle(model, 0, 0, plate_length, plate_width)

extrude_midplane(model, base_sketch, plate_thickness)

with sketch(model, "Front Plane") as hole_sketch:
    for cx, cy in hole_centers:
        sketch_circle(model, cx, cy, hole_radius)

# Through-all cut using stable helper pattern.
extrude_cut(model, hole_sketch, 0)

try:
    chamfer(model, mm(1))
except Exception as exc:
    print("chamfer warning:", exc)

session.save(model, str(part_path))
session.export(model, str(step_path))

print("Saved part:", part_path)
print("Exported STEP:", step_path)