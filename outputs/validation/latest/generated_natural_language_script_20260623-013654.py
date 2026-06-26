from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import os
from sw_session import session
from sw_connect import new_document, save_document, mm
from sw_part import start_sketch, sketch_rectangle, extrude_boss, sketch_circle, extrude_cut, chamfer
from sw_export import export_to_step
from sw_review import run_review

# Define output paths
output_dir = r"C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples"
os.makedirs(output_dir, exist_ok=True)
part_path = os.path.join(output_dir, "mounting_plate.SLDPRT")
step_path = os.path.join(output_dir, "mounting_plate.STEP")

with session() as sw:
    # Create new part document
    new_document("part")
    
    # Sketch base rectangle on Front Plane
    start_sketch("Front Plane")
    sketch_rectangle(mm(0), mm(0), mm(120), mm(80))
    base_extrude = extrude_boss(depth=mm(10))
    
    # Get top face of base extrude for hole sketch
    top_face = base_extrude.GetEndFace()
    start_sketch(top_face)
    
    # Sketch four M6 through holes (6 mm diameter, 10 mm offset from corners)
    hole_radius = mm(3)
    offset = mm(10)
    sketch_circle(offset, offset, hole_radius)
    sketch_circle(mm(120) - offset, offset, hole_radius)
    sketch_circle(offset, mm(80) - offset, hole_radius)
    sketch_circle(mm(120) - offset, mm(80) - offset, hole_radius)
    
    # Extrude cut holes through entire plate
    extrude_cut(depth=mm(10))
    
    # Add 1 mm chamfers to outer plate edges
    outer_edges = base_extrude.GetEdges()
    chamfer(edges=outer_edges, distance=mm(1))
    
    # Save part document
    save_document(part_path)
    
    # Export to STEP
    export_to_step(step_path)
    
    # Generate review report
    run_review(output_dir=output_dir)
