from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

from sw_connect import connect_solidworks, new_document, save_document
from sw_part import start_sketch, sketch_rectangle, extrude_boss, sketch_circle, extrude_cut, chamfer
from sw_export import export_to_step
from sw_review import run_review
import os

# Define output paths
output_dir = r"C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples"
os.makedirs(output_dir, exist_ok=True)
part_path = os.path.join(output_dir, "mounting_plate.SLDPRT")
step_path = os.path.join(output_dir, "mounting_plate.STEP")

# Connect to SolidWorks and create new part
sw = connect_solidworks()
new_document(sw, "part")

# Create base plate: 120x80x10 mm
start_sketch(sw, "Front Plane")
sketch_rectangle(sw, 0, 0, 120, 80)
extrude_boss(sw, 10)

# Add four M6 through holes (6 mm diameter, 10 mm from edges)
start_sketch(sw, "Front Plane")
# Hole positions: (10,10), (110,10), (10,70), (110,70) with 3 mm radius
sketch_circle(sw, 10, 10, 3)
sketch_circle(sw, 110, 10, 3)
sketch_circle(sw, 10, 70, 3)
sketch_circle(sw, 110, 70, 3)
extrude_cut(sw, "through_all")

# Add 1 mm chamfers to outer edges
chamfer(sw, distance=1)

# Save part
save_document(sw, part_path)

# Export to STEP
export_to_step(sw, step_path)

# Run review to generate previews and report
run_review(sw, output_dir=output_dir, part_name="mounting_plate")

print(f"Successfully created mounting plate at: {part_path}")
print(f"STEP export saved at: {step_path}")