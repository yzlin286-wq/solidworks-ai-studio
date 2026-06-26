from __future__ import annotations

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("SWAI_PROJECT_ROOT") or getattr(sys, "_MEIPASS", "") or Path.cwd())
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import os
from sw_session import session
from sw_connect import new_document, save_document, mm
from sw_part import start_sketch, end_sketch, sketch_corner_rectangle, extrude_boss, hole_wizard, chamfer
from sw_export import export_to_step
from sw_review import run_review

# Define output paths (restricted to requested directory)
OUTPUT_DIR = r"C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples"
os.makedirs(OUTPUT_DIR, exist_ok=True)
PART_SAVE_PATH = os.path.join(OUTPUT_DIR, "mounting_plate.SLDPRT")
STEP_EXPORT_PATH = os.path.join(OUTPUT_DIR, "mounting_plate.step")

# Initialize SolidWorks session
sw_app = session()

# Create new part document
part_doc = new_document(sw_app, doc_type="part")

# Create base plate sketch
try:
    start_sketch(part_doc, "Front Plane")
    sketch_corner_rectangle(
        part_doc,
        x1=0,
        y1=0,
        x2=mm(120),
        y2=mm(80)
    )
    end_sketch(part_doc)

    # Extrude base plate 10 mm
    extrude_boss(
        part_doc,
        depth=mm(10),
        name="Base_Plate"
    )

    # Add M6 through holes (10mm offset from each corner)
    hole_positions = [
        (mm(10), mm(10)),
        (mm(110), mm(10)),
        (mm(10), mm(70)),
        (mm(110), mm(70))
    ]
    hole_wizard(
        part_doc,
        standard="ANSI Metric",
        hole_type="Straight Tap Drill",
        size="M6",
        end_condition="Through All",
        positions=hole_positions,
        name="M6_Mounting_Holes"
    )

    # Add 1mm chamfers to all outer edges
    chamfer(
        part_doc,
        distance=mm(1),
        angle=45,
        select_all_outer_edges=True,
        name="1mm_Perimeter_Chamfers"
    )

    # Save SLDPRT file
    save_document(sw_app, part_doc, path=PART_SAVE_PATH)

    # Export STEP file
    export_to_step(part_doc, output_path=STEP_EXPORT_PATH)

    # Run automated review
    run_review(part_doc, output_dir=OUTPUT_DIR)

finally:
    # Clean up: close document without prompting (changes already saved)
    sw_app.CloseDoc(PART_SAVE_PATH, False)
