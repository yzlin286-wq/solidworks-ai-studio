from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

from pathlib import Path
# Import vendored SolidWorks automation modules
from sw_session import session
from sw_connect import new_document, find_template, save_document, mm
from sw_part import start_sketch, end_sketch, sketch_rectangle, add_dimension, extrude_boss, sketch_circle, extrude_cut, chamfer
from sw_export import export_to_step
from sw_review import run_review

# Define output paths
OUTPUT_DIR = Path(r"C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PART_PATH = OUTPUT_DIR / "mounting_plate.SLDPRT"
STEP_PATH = OUTPUT_DIR / "mounting_plate.stp"

# Connect to SolidWorks session
sw_app = session()

# Create new part document with mm units
part_template = find_template(doc_type="part")
new_document(template_path=part_template, doc_type="part")

# Step 1: Create base plate 120x80x10 mm
start_sketch(plane="Front Plane")
# Sketch 120x80 mm rectangle from origin
sketch_rectangle(x1=0, y1=0, x2=120, y2=80)
# Add dimensions to fully define sketch
add_dimension(horizontal=mm(120), vertical=mm(80))
end_sketch()
# Extrude 10 mm depth
extrude_boss(depth=mm(10))

# Step 2: Add four M6 through holes (6 mm diameter, 10 mm from edges)
start_sketch(plane="Front Plane")
HOLE_DIAMETER = mm(6)
HOLE_CENTERS = [
    (mm(10), mm(10)),
    (mm(110), mm(10)),
    (mm(10), mm(70)),
    (mm(110), mm(70))
]
for x, y in HOLE_CENTERS:
    sketch_circle(x=x, y=y, radius=HOLE_DIAMETER / 2)
end_sketch()
# Cut holes through entire plate thickness
extrude_cut(depth="through_all")

# Step 3: Add 1 mm chamfers to outer plate edges
chamfer(distance=mm(1), edge_selection="outer_perimeter")

# Step 4: Save part and export STEP
save_document(file_path=str(PART_PATH))
export_to_step(output_path=str(STEP_PATH))

# Step 5: Run review to generate previews and report
run_review(output_directory=str(OUTPUT_DIR))