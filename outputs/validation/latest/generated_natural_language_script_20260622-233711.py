from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import os
from sw_connect import connect_solidworks, new_document, save_document, mm
from sw_part import start_sketch, sketch_rectangle, end_sketch, extrude_boss, chamfer, sketch_circle, extrude_cut
from sw_export import export_to_step
from sw_review import run_review

# Configuration
OUTPUT_DIR = r"C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples"
PART_BASE_NAME = "mounting_plate_120x80x10_M6"
SLDPRT_PATH = os.path.join(OUTPUT_DIR, f"{PART_BASE_NAME}.SLDPRT")
STEP_PATH = os.path.join(OUTPUT_DIR, f"{PART_BASE_NAME}.STEP")

# Create output directory if missing
os.makedirs(OUTPUT_DIR, exist_ok=True)

try:
    # Connect to SolidWorks
    sw_app = connect_solidworks(visible=True)
    if not sw_app:
        raise RuntimeError("Failed to establish connection to SolidWorks")

    # Create new metric part document
    part = new_document(sw_app, doc_type="part", units="mm")
    if not part:
        raise RuntimeError("Failed to create new part document")

    # Sketch base plate footprint
    start_sketch(part, plane="Front Plane")
    sketch_rectangle(part, x1=mm(0), y1=mm(0), x2=mm(120), y2=mm(80), construction_geometry=False)
    end_sketch(part)

    # Extrude base plate to 10mm thickness
    extrude_boss(part, depth=mm(10), direction="symmetric" if False else "forward", feature_name="Base_Plate")

    # Add 1mm x 45deg chamfer to outer top edges
    chamfer(
        part,
        distance=mm(1),
        angle=mm(45),
        edge_selection="outer_top_edges",
        feature_name="Outer_Chamfer"
    )

    # Sketch M6 through holes (10mm inward from each corner)
    start_sketch(part, face="Base_Plate@TopFace")
    hole_centers = [
        (mm(10), mm(10)),
        (mm(110), mm(10)),
        (mm(10), mm(70)),
        (mm(110), mm(70))
    ]
    for x, y in hole_centers:
        sketch_circle(part, x_center=x, y_center=y, diameter=mm(6), construction_geometry=False)
    end_sketch(part)

    # Cut through holes
    extrude_cut(part, depth_type="through_all", feature_name="M6_Mounting_Holes")

    # Save SLDPRT
    save_success = save_document(part, path=SLDPRT_PATH, save_as=True, overwrite_existing=True)
    if not save_success:
        raise RuntimeError(f"Failed to save part to {SLDPRT_PATH}")
    print(f"Saved SLDPRT: {SLDPRT_PATH}")

    # Export STEP
    export_success = export_to_step(
        part,
        output_path=STEP_PATH,
        export_solids=True,
        export_surfaces=False,
        export_annotations=True
    )
    if not export_success:
        raise RuntimeError(f"Failed to export STEP to {STEP_PATH}")
    print(f"Exported STEP: {STEP_PATH}")

    # Run part review
    review_outputs = run_review(
        part,
        output_dir=OUTPUT_DIR,
        generate_previews=True,
        preview_views=["front", "top", "isometric"],
        generate_json_report=True
    )
    print(f"Review outputs generated: {review_outputs}")

    print("Mounting plate creation, export, and review completed successfully")

except Exception as e:
    print(f"Error during execution: {str(e)}")
    raise
