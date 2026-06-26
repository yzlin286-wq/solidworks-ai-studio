from __future__ import annotations

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("SWAI_PROJECT_ROOT") or getattr(sys, "_MEIPASS", "") or Path.cwd())
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import os
from pathlib import Path

# Import vendored SolidWorks automation modules
from sw_connect import connect_solidworks, new_document, save_document, mm
from sw_part import (
    start_sketch, end_sketch, sketch_corner_rectangle, sketch_circle,
    add_dimension, extrude_boss, extrude_cut, chamfer
)
from sw_export import export_to_step
from sw_review import run_review

# Configuration
OUTPUT_DIR = Path("C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples")
PART_NAME = "mounting_plate_120x80x10"
M6_HOLE_DIAMETER = 6.6 * mm
HOLE_OFFSET = 10 * mm
PLATE_WIDTH = 120 * mm
PLATE_HEIGHT = 80 * mm
PLATE_THICKNESS = 10 * mm
CHAMFER_SIZE = 1 * mm

def main():
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    part_path = OUTPUT_DIR / f"{PART_NAME}.SLDPRT"
    step_path = OUTPUT_DIR / f"{PART_NAME}.step"

    # Connect to SolidWorks
    sw_app = connect_solidworks()

    # Create new part document
    part = new_document(sw_app, "part")
    model = part.ModelDoc2

    # Sketch base plate rectangle
    start_sketch(model, "Front Plane")
    sketch_corner_rectangle(model, 0, 0, PLATE_WIDTH, PLATE_HEIGHT)
    add_dimension(model, "D1", PLATE_WIDTH)
    add_dimension(model, "D2", PLATE_HEIGHT)
    end_sketch(model)

    # Extrude base plate
    extrude_boss(model, "Sketch1", PLATE_THICKNESS)

    # Sketch hole centers on top face
    start_sketch(model, "Top Plane")
    # Hole 1: Bottom-left corner offset
    sketch_circle(model, HOLE_OFFSET, HOLE_OFFSET, M6_HOLE_DIAMETER / 2)
    # Hole 2: Bottom-right corner offset
    sketch_circle(model, PLATE_WIDTH - HOLE_OFFSET, HOLE_OFFSET, M6_HOLE_DIAMETER / 2)
    # Hole 3: Top-left corner offset
    sketch_circle(model, HOLE_OFFSET, PLATE_HEIGHT - HOLE_OFFSET, M6_HOLE_DIAMETER / 2)
    # Hole 4: Top-right corner offset
    sketch_circle(model, PLATE_WIDTH - HOLE_OFFSET, PLATE_HEIGHT - HOLE_OFFSET, M6_HOLE_DIAMETER / 2)
    end_sketch(model)

    # Extrude cut holes through entire plate
    extrude_cut(model, "Sketch2", PLATE_THICKNESS, through_all=True)

    # Apply 1 mm chamfers to all outer edges and hole edges
    # Select all outer edges first
    model.Extension.SelectAllEdges()
    chamfer(model, CHAMFER_SIZE, CHAMFER_SIZE)
    model.ClearSelection2(True)

    # Save part
    save_document(model, str(part_path))

    # Export to STEP
    export_to_step(model, str(step_path))

    # Run review to generate previews and report
    run_review(model, OUTPUT_DIR)

    print(f"Successfully created mounting plate:")
    print(f"  SLDPRT: {part_path}")
    print(f"  STEP: {step_path}")
    print(f"  Review files in: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
