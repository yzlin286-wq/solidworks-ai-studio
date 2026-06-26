from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import os
from sw_connect import connect_solidworks, new_document, save_document, mm
from sw_part import start_sketch, sketch_rectangle, end_sketch, extrude_boss, hole_wizard, chamfer
from sw_export import export_to_step
from sw_review import run_review

# Define output directory
OUTPUT_DIR = r"C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def main():
    # Connect to SolidWorks
    sw = connect_solidworks()
    if not sw:
        raise RuntimeError("Failed to connect to SolidWorks - ensure it is running")
    
    # Create new part document
    part = new_document(sw, "part")
    if not part:
        raise RuntimeError("Failed to create new part document")
    
    # Sketch base plate outline
    start_sketch(part, "Front Plane")
    sketch_rectangle(part, 0, 0, 120*mm, 80*mm)
    end_sketch(part)
    
    # Extrude to create plate thickness
    extrude_boss(part, depth=10*mm)
    
    # Define M6 hole positions (10 mm offset from each edge)
    hole_positions = [
        (10*mm, 10*mm),
        (110*mm, 10*mm),
        (10*mm, 70*mm),
        (110*mm, 70*mm)
    ]
    
    # Create M6 through holes
    hole_wizard(
        part,
        standard="ISO",
        hole_type="Clearance Hole",
        size="M6",
        termination="Through All",
        positions=hole_positions,
        sketch_plane="Front Plane"
    )
    
    # Add 1 mm chamfers to outer edges
    chamfer(
        part,
        distance=1*mm,
        edges="All Outer Edges"
    )
    
    # Save SLDPRT
    part_path = os.path.join(OUTPUT_DIR, "mounting_plate.SLDPRT")
    save_document(sw, part, part_path)
    
    # Export STEP
    step_path = os.path.join(OUTPUT_DIR, "mounting_plate.stp")
    export_to_step(part, step_path)
    
    # Generate review report
    run_review(part, output_dir=OUTPUT_DIR)
    
    print(f"Successfully created mounting plate at: {part_path}")
    print(f"STEP export: {step_path}")

if __name__ == "__main__":
    main()