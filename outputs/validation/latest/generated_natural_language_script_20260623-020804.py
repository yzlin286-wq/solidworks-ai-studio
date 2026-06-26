from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import os
from pathlib import Path

# Import vendored SolidWorks automation modules
from sw_connect import connect_solidworks, new_document, save_document, mm, find_template
from sw_part import (
    start_sketch,
    end_sketch,
    sketch_rectangle,
    sketch_circle,
    extrude_boss,
    extrude_cut,
    chamfer,
    add_dimension
)
from sw_export import export_to_step
from sw_review import run_review

# Configuration
OUTPUT_DIR = Path(r"C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples")
PART_NAME = "mounting_plate"
SLDPRT_PATH = OUTPUT_DIR / f"{PART_NAME}.SLDPRT"
STEP_PATH = OUTPUT_DIR / f"{PART_NAME}.step"

def main():
    # Create output directory if missing
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Connect to SolidWorks
    sw_app, _, _ = connect_solidworks(visible=True)
    if not sw_app:
        raise RuntimeError("Failed to connect to SolidWorks")

    # Create new part document
    part_template = find_template("part")
    part_doc = new_document(sw_app, part_template)
    if not part_doc:
        raise RuntimeError("Failed to create new part document")

    # Sketch base plate rectangle
    start_sketch(part_doc, "Front Plane")
    sketch_rectangle(part_doc, x1=mm(0), y1=mm(0), x2=mm(120), y2=mm(80))
    add_dimension(part_doc, mm(120), "Plate Length")
    add_dimension(part_doc, mm(80), "Plate Width")
    end_sketch(part_doc)

    # Extrude base plate to 10 mm thickness
    extrude_boss(part_doc, depth=mm(10))

    # Sketch M6 through holes (10 mm offset from edges)
    start_sketch(part_doc, "Front Plane")
    hole_radius = mm(3)  # 6 mm diameter = 3 mm radius for M6
    hole_positions = [
        (mm(10), mm(10)),
        (mm(110), mm(10)),
        (mm(10), mm(70)),
        (mm(110), mm(70))
    ]
    for x, y in hole_positions:
        sketch_circle(part_doc, center_x=x, center_y=y, radius=hole_radius)
    add_dimension(part_doc, mm(6), "M6 Hole Diameter")
    end_sketch(part_doc)

    # Extrude cut through full plate thickness
    extrude_cut(part_doc, through_all=True)

    # Add 1 mm chamfer to outer plate edges
    chamfer(part_doc, distance=mm(1), angle=45, edge_selection="outer_perimeter")

    # Save SLDPRT file
    save_document(part_doc, str(SLDPRT_PATH))

    # Export STEP file
    export_to_step(part_doc, str(STEP_PATH))

    # Run review and generate outputs
    run_review(part_doc, output_dir=str(OUTPUT_DIR))

    print(f"Successfully created part: {SLDPRT_PATH}")
    print(f"Exported STEP: {STEP_PATH}")
    print(f"Review outputs saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
