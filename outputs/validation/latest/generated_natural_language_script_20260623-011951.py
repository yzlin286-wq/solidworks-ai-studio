from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import os

# Import vendored SolidWorks automation utilities
from sw_session import session
from sw_connect import mm, new_document, save_document
from sw_part import start_sketch, sketch_corner_rectangle, extrude_boss, sketch_circle, extrude_cut, chamfer
from sw_export import export_to_step
from sw_review import run_review

# Define output paths (restricted to user-specified directory)
OUTPUT_DIR = r"C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples"
os.makedirs(OUTPUT_DIR, exist_ok=True)
PART_PATH = os.path.join(OUTPUT_DIR, "mounting_plate.SLDPRT")
STEP_PATH = os.path.join(OUTPUT_DIR, "mounting_plate.stp")

def create_mounting_plate():
    # Managed SolidWorks session with automatic cleanup
    with session() as sw_app:
        # Create new part document
        part = new_document(sw_app, doc_type="part")

        # Step 1: Create base plate solid
        start_sketch(part, plane="Front Plane")
        sketch_corner_rectangle(x1=mm(0), y1=mm(0), x2=mm(120), y2=mm(80))
        extrude_boss(depth=mm(10))

        # Step 2: Add four M6 through holes (6mm diameter, 10mm offset from corners)
        HOLE_DIAMETER = mm(6)
        HOLE_OFFSET = mm(10)
        hole_positions = [
            (HOLE_OFFSET, HOLE_OFFSET),
            (mm(120) - HOLE_OFFSET, HOLE_OFFSET),
            (HOLE_OFFSET, mm(80) - HOLE_OFFSET),
            (mm(120) - HOLE_OFFSET, mm(80) - HOLE_OFFSET)
        ]

        start_sketch(part, face="Top Face")
        for x, y in hole_positions:
            sketch_circle(x=x, y=y, diameter=HOLE_DIAMETER)
        extrude_cut(through_all=True)

        # Step 3: Add 1mm chamfers to outer edges
        chamfer(distance=mm(1), edges="Outer Perimeter Edges")

        # Step 4: Save part file
        save_document(part, PART_PATH, save_as=True)

        # Step 5: Export STEP file
        export_to_step(part, STEP_PATH)

        # Step 6: Generate review report and previews
        run_review(part, output_dir=OUTPUT_DIR)

        print(f"Successfully created mounting plate:")
        print(f"  Part: {PART_PATH}")
        print(f"  STEP: {STEP_PATH}")
        print(f"  Review outputs: {OUTPUT_DIR}")

if __name__ == "__main__":
    create_mounting_plate()
