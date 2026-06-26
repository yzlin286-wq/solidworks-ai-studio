from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

{
  "plan": [
    "Create the specified output directory if it does not exist to ensure valid write paths",
    "Establish a COM connection to a running SolidWorks instance or launch a new instance",
    "Create a new part document using the default SolidWorks part template",
    "Sketch a 120x80 mm rectangular profile on the Top Plane, then extrude to 10 mm thickness to form the base plate",
    "Sketch four 6 mm diameter circles for M6 through holes, positioned 10 mm from each plate corner",
    "Extrude cut through the full plate thickness to create the four through holes",
    "Apply 1 mm chamfers to all outer edges of the mounting plate",
    "Save the completed part as a SLDPRT file to the output directory",
    "Export the part to STEP format and save to the same output directory",
    "Execute the SolidWorks review tool to generate preview images and a JSON validation report for the part"
  ],
  "risks": [
    "SolidWorks COM connection failure if SolidWorks is not installed, running, or properly registered",
    "Missing default part template error if SolidWorks installation templates are not found",
    "Feature creation failures from overdefined sketches, invalid geometry, or incorrect feature parameters",
    "File system permission errors when writing to the specified output directory",
    "Hole positioning errors if offset values result in holes outside the plate boundaries",
    "STEP export failures due to invalid geometry or missing SolidWorks export licenses",
    "Review tool errors if the active document has rebuild errors or corrupted geometry"
  ],
  "required_files": [
    r"C:\Users\Vision\Documents\sw skill 应用化\vendor\skills\solidworks-automation\scripts\sw_connect.py",
    r"C:\Users\Vision\Documents\sw skill 应用化\vendor\skills\solidworks-automation\scripts\sw_part.py",
    r"C:\Users\Vision\Documents\sw skill 应用化\vendor\skills\solidworks-automation\scripts\sw_export.py",
    r"C:\Users\Vision\Documents\sw skill 应用化\vendor\skills\solidworks-automation\scripts\sw_review.py",
    "SolidWorks default part template (automatically located via sw_connect.find_template)"
  ],
  "script": "import os\nimport sys\n\n# Add vendored SolidWorks automation scripts to Python path\nVENDOR_SCRIPTS_DIR = r\"C:\\Users\\Vision\\Documents\\sw skill 应用化\\vendor\\skills\\solidworks-automation\\scripts\"\nif VENDOR_SCRIPTS_DIR not in sys.path:\n    sys.path.insert(0, VENDOR_SCRIPTS_DIR)\n\n# Import vendored SolidWorks automation modules\nfrom sw_connect import connect_solidworks, new_document, save_document, mm\nfrom sw_part import start_sketch, sketch_corner_rectangle, extrude_boss, sketch_circle, extrude_cut, chamfer, end_sketch\nfrom sw_export import export_to_step\nfrom sw_review import run_review\n\n# Define output paths\nOUTPUT_DIR = r\"C:\\Users\\Vision\\Documents\\sw skill 应用化\\outputs\\validation\\latest\\cad_samples\"\nos.makedirs(OUTPUT_DIR, exist_ok=True)\nPART_FILENAME = \"mounting_plate_120x80x10_M6\"\nPART_SAVE_PATH = os.path.join(OUTPUT_DIR, f\"{PART_FILENAME}.SLDPRT\")\nSTEP_SAVE_PATH = os.path.join(OUTPUT_DIR, f\"{PART_FILENAME}.STEP\")\n\nif __name__ == \"__main__\":\n    # Connect to SolidWorks\n    sw_app = connect_solidworks()\n    print(\"Successfully connected to SolidWorks\")\n\n    # Create new part document\n    part_doc = new_document(sw_app, doc_type=\"part\")\n    print(\"Created new part document\")\n\n    # Create base plate extrusion\n    start_sketch(\"Top Plane\")\n    sketch_corner_rectangle(\n        x1=mm(0), y1=mm(0),\n        x2=mm(120), y2=mm(80)\n    )\n    end_sketch()\n    extrude_boss(depth=mm(10), feature_name=\"Base_Plate\")\n    print(\"Created 120x80x10 mm base plate\")\n\n    # Create M6 through holes (6mm diameter, 10mm offset from corners)\n    HOLE_DIAMETER = mm(6)\n    HOLE_OFFSET = mm(10)\n    PLATE_LENGTH = mm(120)\n    PLATE_WIDTH = mm(80)\n\n    start_sketch(\"Top Plane\")\n    # Four corner hole positions\n    sketch_circle(x=HOLE_OFFSET, y=HOLE_OFFSET, radius=HOLE_DIAMETER / 2)\n    sketch_circle(x=PLATE_LENGTH - HOLE_OFFSET, y=HOLE_OFFSET, radius=HOLE_DIAMETER / 2)\n    sketch_circle(x=PLATE_LENGTH - HOLE_OFFSET, y=PLATE_WIDTH - HOLE_OFFSET, radius=HOLE_DIAMETER / 2)\n    sketch_circle(x=HOLE_OFFSET, y=PLATE_WIDTH - HOLE_OFFSET, radius=HOLE_DIAMETER / 2)\n    end_sketch()\n\n    extrude_cut(termination=\"through_all\", feature_name=\"M6_Through_Holes\")\n    print(\"Created four M6 through holes\")\n\n    # Add 1mm chamfers to outer edges\n    chamfer(distance=mm(1), select_outer_edges=True, feature_name=\"Outer_Edge_Chamfers\")\n    print(\"Applied 1mm chamfers to outer edges\")\n\n    # Save SLDPRT\n    save_document(sw_app, part_doc, save_path=PART_SAVE_PATH, overwrite=True)\n    print(f\"Saved part to: {PART_SAVE_PATH}\")\n\n    # Export STEP\n    export_to_step(part_doc, output_path=STEP_SAVE_PATH, export_annotations=False)\n    print(f\"Exported STEP to: {STEP_SAVE_PATH}\")\n\n    # Run review and save outputs\n    run_review(part_doc, output_directory=OUTPUT_DIR, generate_previews=True)\n    print(f\"Review completed, outputs saved to: {OUTPUT_DIR}\")\n\n    print(\"Mounting plate creation, export, and review completed successfully\")"
}