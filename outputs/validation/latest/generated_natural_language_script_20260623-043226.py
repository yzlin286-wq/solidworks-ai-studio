from __future__ import annotations

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("SWAI_PROJECT_ROOT") or getattr(sys, "_MEIPASS", "") or Path.cwd())
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import sys
import os

# Add vendored SolidWorks automation scripts to Python path
sys.path.insert(0, r"C:\Users\Vision\Documents\sw skill 应用化\vendor\skills\solidworks-automation\scripts")

from sw_session import session
import sw_part
import sw_export
import sw_review

# Define output paths
OUTPUT_DIR = r"C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PART_BASE_NAME = "mounting_plate_120x80x10_M6"
SLDPRT_PATH = os.path.join(OUTPUT_DIR, f"{PART_BASE_NAME}.SLDPRT")
STEP_PATH = os.path.join(OUTPUT_DIR, f"{PART_BASE_NAME}.step")

def get_outer_perimeter_edges(part, top_face):
    """Helper to filter only outer perimeter edges from the top face, excluding hole edges"""
    edges = top_face.GetEdges()
    outer_edges = []
    for edge in edges:
        # Filter edges with length matching outer plate dimensions (120 or 80 mm)
        length = edge.GetLength() * 1000  # Convert SW meters to mm
        if abs(length - 120) < 0.1 or abs(length - 80) < 0.1:
            outer_edges.append(edge)
    return outer_edges

if __name__ == "__main__":
    with session(visible=True) as sw:
        # Create new part document
        part = sw.new_document(doc_type="part")
        
        # Sketch base plate outline on Top Plane
        sw_part.start_sketch(part, plane_name="Top Plane")
        sw_part.sketch_corner_rectangle(part, x1=0, y1=0, x2=120, y2=80)
        # Fully define sketch with dimensions
        sw_part.add_dimension(part, entity_name="Horizontal Line", value=120, mm=True)
        sw_part.add_dimension(part, entity_name="Vertical Line", value=80, mm=True)
        sw_part.add_sketch_relation(part, entity1="Sketch Origin", entity2="Lower Left Corner", relation="Coincident")
        sw_part.end_sketch(part)
        
        # Extrude base plate to 10mm thickness
        sw_part.extrude_boss(part, depth=10, mm=True)
        
        # Get top face of the extruded plate for hole sketch
        top_face = part.Extension.GetFirstFaceByNormal((0, 0, 1))
        
        # Sketch M6 through holes (6mm diameter, 10mm offset from each corner)
        HOLE_DIAMETER = 6
        EDGE_OFFSET = 10
        hole_positions = [
            (EDGE_OFFSET, EDGE_OFFSET),
            (120 - EDGE_OFFSET, EDGE_OFFSET),
            (EDGE_OFFSET, 80 - EDGE_OFFSET),
            (120 - EDGE_OFFSET, 80 - EDGE_OFFSET)
        ]
        
        sw_part.start_sketch(part, entity=top_face)
        for idx, (x, y) in enumerate(hole_positions, 1):
            sw_part.sketch_circle(part, x=x, y=y, radius=HOLE_DIAMETER / 2)
            # Dimension hole position and size
            sw_part.add_dimension(part, entity_name=f"Circle{idx}", value=HOLE_DIAMETER, mm=True)
        sw_part.end_sketch(part)
        
        # Extrude cut holes through entire plate
        sw_part.extrude_cut(part, through_all=True, mm=True)
        
        # Apply 1mm chamfer to outer top edges
        outer_edges = get_outer_perimeter_edges(part, top_face)
        sw_part.chamfer(part, edges=outer_edges, distance=1, angle=45, mm=True)
        
        # Save finished part
        sw.save_document(part, path=SLDPRT_PATH)
        
        # Export to STEP format
        sw_export.export_to_step(part, output_path=STEP_PATH)
        
        # Run automated review to generate previews and report
        sw_review.run_review(part, output_dir=OUTPUT_DIR, report_name=f"{PART_BASE_NAME}_review")
        
        print(f"Successfully generated mounting plate files in: {OUTPUT_DIR}")