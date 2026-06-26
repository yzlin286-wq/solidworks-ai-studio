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
VENDOR_SCRIPTS = r"C:\Users\Vision\Documents\sw skill 应用化\vendor\skills\solidworks-automation\scripts"
sys.path.insert(0, VENDOR_SCRIPTS)

from sw_connect import connect_solidworks, new_document, save_document
from sw_part import (
    start_sketch,
    end_sketch,
    sketch_rectangle,
    extrude_boss,
    sketch_circle,
    extrude_cut,
    chamfer
)
from sw_export import export_to_step
from sw_review import run_review

def create_mounting_plate(output_dir: str):
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Define output file paths
    part_file = os.path.join(output_dir, "mounting_plate_120x80x10.SLDPRT")
    step_file = os.path.join(output_dir, "mounting_plate_120x80x10.STEP")
    
    # Connect to SolidWorks application
    sw_app = connect_solidworks()
    if not sw_app:
        raise RuntimeError("Failed to establish connection to SolidWorks application")
    
    try:
        # Create new part document
        part = new_document(sw_app, "part")
        if not part:
            raise RuntimeError("Failed to create new SolidWorks part document")
        
        # 1. Sketch plate outline (120x80 mm)
        start_sketch(part, "Top Plane")
        sketch_rectangle(part, x1=0, y1=0, x2=120, y2=80)  # Units: millimeters
        end_sketch(part)
        
        # 2. Extrude to 10 mm thickness
        extrude_boss(part, depth=10)
        
        # 3. Sketch M6 through holes (6 mm diameter, 10 mm from corners)
        start_sketch(part, "Top Plane")
        sketch_circle(part, x=10, y=10, radius=3)   # 3 mm radius = 6 mm diameter
        sketch_circle(part, x=110, y=10, radius=3)
        sketch_circle(part, x=110, y=70, radius=3)
        sketch_circle(part, x=10, y=70, radius=3)
        end_sketch(part)
        
        # 4. Extrude cut through entire plate thickness
        extrude_cut(part, through_all=True)
        
        # 5. Add 1 mm chamfers to outer perimeter edges
        chamfer(part, distance=1)
        
        # 6. Save part to SLDPRT
        save_document(sw_app, part, part_file)
        
        # 7. Export to STEP format
        export_to_step(part, step_file)
        
        # 8. Generate review report and previews
        run_review(part, output_dir)
        
        return {
            "part_saved": part_file,
            "step_exported": step_file,
            "review_generated": True
        }
    except Exception as e:
        raise RuntimeError(f"Mounting plate creation failed: {str(e)}")

if __name__ == "__main__":
    output_directory = r"C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples"
    result = create_mounting_plate(output_directory)
    print(f"Operation completed successfully: {result}")