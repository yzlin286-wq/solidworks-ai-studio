from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import os
from sw_connect import connect_solidworks, new_document, find_template, save_document
from sw_part import start_sketch, sketch_corner_rectangle, extrude_boss, sketch_circle, extrude_cut, chamfer, end_sketch
from sw_export import export_to_step
from sw_review import run_review

# Configuration
output_dir = r"C:\Users\Vision\Documents\sw skill 应用化\outputs\validation\latest\cad_samples"
part_name = "mounting_plate_120x80x10"
sldprt_path = os.path.join(output_dir, f"{part_name}.SLDPRT")
step_path = os.path.join(output_dir, f"{part_name}.step")

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Connect to SolidWorks
sw_app = connect_solidworks()

# Get part template path
part_template = find_template("part")

# Create new part document
model = new_document(sw_app, part_template)

# Step 1: Create base plate sketch
start_sketch(model, "Front Plane")
sketch_corner_rectangle(model, 0, 0, 120, 80)
end_sketch(model)

# Step 2: Extrude base plate (10mm thickness)
extrude_boss(model, 10.0)

# Step 3: Create M6 through holes (4 holes, 10mm offset from corners)
start_sketch(model, "Front Plane")
# Hole centers: (10,10), (110,10), (10,70), (110,70) | Diameter 6mm (radius 3mm)
sketch_circle(model, 10, 10, 3.0)
sketch_circle(model, 110, 10, 3.0)
sketch_circle(model, 10, 70, 3.0)
sketch_circle(model, 110, 70, 3.0)
end_sketch(model)

# Step 4: Extrude cut through all to create holes
extrude_cut(model, "Through All")

# Step 5: Add 1mm chamfers to outer edges
# Retrieve the first boss extrude feature (base plate)
feature = model.FirstFeature
boss_feature = None
while feature:
    if feature.GetTypeName() == "BossExtrude":
        boss_feature = feature
        break
    feature = feature.GetNextFeature()

if boss_feature:
    # Get the top face of the base plate
    face = boss_feature.GetFirstFace()
    # Get all edges of the face (outer perimeter)
    edges = face.GetEdges()
    # Select each edge for chamfer (append selection)
    for edge in edges:
        model.SelectByID2(edge.Name, "EDGE", 0, 0, 0, True, 0, None, 0)
    # Apply 1mm x 45° chamfer
    chamfer(model, 1.0, 45.0)

# Step 6: Save the part
save_document(model, sldprt_path)

# Step 7: Export to STEP
export_to_step(model, step_path)

# Step 8: Run review to generate previews and report
run_review(model, output_dir)