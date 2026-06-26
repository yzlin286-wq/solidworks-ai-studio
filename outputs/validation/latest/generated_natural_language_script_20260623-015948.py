from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import os
from sw_session import session
from sw_connect import mm, deg, new_document, save_document
from sw_part import start_sketch, sketch_rectangle, end_sketch, extrude_boss, sketch_circle, extrude_cut, chamfer
from sw_export import export_to_step
from sw_review import run_review

# Configuration
OUTPUT_DIR = r"C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples"
PART_FILENAME = "mounting_plate_120x80x10.SLDPRT"
STEP_FILENAME = "mounting_plate_120x80x10.STEP"
PART_PATH = os.path.join(OUTPUT_DIR, PART_FILENAME)
STEP_PATH = os.path.join(OUTPUT_DIR, STEP_FILENAME)

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_mounting_plate():
    # Connect to SolidWorks
    sw = session()
    
    # Create new part document
    new_document(sw, doc_type="part")
    
    # Step 1: Create base plate sketch
    start_sketch(sw, plane_name="Top Plane")
    # 120x80 mm rectangle, corner at origin
    sketch_rectangle(sw, x1=mm(0), y1=mm(0), x2=mm(120), y2=mm(80))
    end_sketch(sw)
    
    # Step 2: Extrude base plate to 10 mm thickness
    extrude_boss(sw, depth=mm(10), direction="blind")
    
    # Step 3: Sketch M6 through holes (6.5 mm diameter, 10 mm from edges)
    start_sketch(sw, plane_name="Top Plane")
    hole_radius = mm(6.5 / 2)  # Standard M6 medium clearance hole
    hole_centers = [
        (mm(10), mm(10)),
        (mm(110), mm(10)),
        (mm(10), mm(70)),
        (mm(110), mm(70))
    ]
    for x, y in hole_centers:
        sketch_circle(sw, x=x, y=y, radius=hole_radius)
    end_sketch(sw)
    
    # Step 4: Extrude cut holes through entire plate
    extrude_cut(sw, depth=mm(10), through_all=True)
    
    # Step 5: Add 1 mm 45° chamfers to all outer edges
    chamfer(sw, distance=mm(1), angle=deg(45), select_outer_edges=True)
    
    # Step 6: Save SLDPRT
    save_document(sw, filepath=PART_PATH, overwrite=True)
    
    # Step 7: Export STEP
    export_to_step(sw, filepath=STEP_PATH, overwrite=True)
    
    # Step 8: Run review
    review_results = run_review(sw, output_dir=OUTPUT_DIR, part_name="mounting_plate_120x80x10")
    
    return {
        "sldprt_path": PART_PATH,
        "step_path": STEP_PATH,
        "review_results": review_results
    }

if __name__ == "__main__":
    result = create_mounting_plate()
    print(f"Successfully created mounting plate:")
    print(f"SLDPRT: {result['sldprt_path']}")
    print(f"STEP: {result['step_path']}")
    print(f"Review completed: {result['review_results']}")