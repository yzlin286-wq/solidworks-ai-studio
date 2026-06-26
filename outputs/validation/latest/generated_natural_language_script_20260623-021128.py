from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import os
from sw_session import session
from sw_part import start_sketch, sketch_corner_rectangle, extrude_boss, sketch_circle, extrude_cut, chamfer
from sw_export import export_to_step
from sw_review import run_review

# Define output paths
OUTPUT_DIR = r"C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples"
PART_PATH = os.path.join(OUTPUT_DIR, "mounting_plate.SLDPRT")
STEP_PATH = os.path.join(OUTPUT_DIR, "mounting_plate.step")

def create_mounting_plate():
    with session() as sw:
        # Create new part document
        part = sw.new_document("part")
        
        # Step 1: Create base plate extrusion
        start_sketch(part, "Top Plane")
        # 120x80 mm rectangle centered at origin (-60,-40 to 60,40)
        sketch_corner_rectangle(part, -60, -40, 60, 40)
        extrude_boss(part, depth=10)
        
        # Step 2: Create M6 through holes (6mm diameter, 10mm from edges)
        # Get top face of the base extrusion
        base_extrusion = part.FeatureManager.FeatureByName("Boss-Extrude1")
        top_face = base_extrusion.GetFaces()[1]
        start_sketch(part, top_face)
        # Sketch four holes at (-50,-30), (50,-30), (-50,30), (50,30)
        sketch_circle(part, -50, -30, 6)
        sketch_circle(part, 50, -30, 6)
        sketch_circle(part, -50, 30, 6)
        sketch_circle(part, 50, 30, 6)
        extrude_cut(part, through_all=True)
        
        # Step 3: Add 1mm chamfers to outer edges
        bottom_face = base_extrusion.GetFaces()[0]
        # Chamfer top face perimeter edges
        chamfer(part, distance=1, edges=top_face.GetEdges())
        # Chamfer bottom face perimeter edges
        chamfer(part, distance=1, edges=bottom_face.GetEdges())
        
        # Step 4: Save part
        sw.save_document(part, PART_PATH)
        
        # Step 5: Export to STEP
        export_to_step(part, STEP_PATH)
        
        # Step 6: Run review
        run_review(part, OUTPUT_DIR)
        
        print(f"Successfully created mounting plate at: {PART_PATH}")
        print(f"STEP export saved to: {STEP_PATH}")

if __name__ == "__main__":
    create_mounting_plate()