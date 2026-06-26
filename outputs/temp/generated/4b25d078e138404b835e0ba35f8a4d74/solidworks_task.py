from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import os
from vendor.skills.solidworks_automation.scripts import SolidWorksSession, sw_part, sw_export

# --------------------------
# USER CONFIGURATION (EDIT ME)
# --------------------------
# Set this to your selected workspace output directory
OUTPUT_DIRECTORY = r"C:\Your\Workspace\Output"
PART_BASE_NAME = "mounting_plate_120x80x10"

# --------------------------
# VALIDATION (DO NOT EDIT)
# --------------------------
if not os.path.isdir(OUTPUT_DIRECTORY):
    raise NotADirectoryError(f"Output directory does not exist: {OUTPUT_DIRECTORY}")
if not os.access(OUTPUT_DIRECTORY, os.W_OK):
    raise PermissionError(f"No write access to output directory: {OUTPUT_DIRECTORY}")

# --------------------------
# PART PARAMETERS (DO NOT EDIT)
# --------------------------
PLATE_LENGTH = 120.0    # mm
PLATE_WIDTH = 80.0      # mm
PLATE_THICKNESS = 10.0  # mm
HOLE_DIAMETER = 6.0     # M6 through hole diameter
HOLE_EDGE_OFFSET = 10.0 # mm offset from plate edges
CHAMFER_DISTANCE = 1.0  # mm
CHAMFER_ANGLE = 45.0    # degrees

# Calculate hole center positions (origin at bottom-left corner of plate)
hole_positions = [
    (HOLE_EDGE_OFFSET, HOLE_EDGE_OFFSET),                    # Bottom-left
    (PLATE_LENGTH - HOLE_EDGE_OFFSET, HOLE_EDGE_OFFSET),     # Bottom-right
    (PLATE_LENGTH - HOLE_EDGE_OFFSET, PLATE_WIDTH - HOLE_EDGE_OFFSET), # Top-right
    (HOLE_EDGE_OFFSET, PLATE_WIDTH - HOLE_EDGE_OFFSET)       # Top-left
]

# --------------------------
# WORKFLOW EXECUTION (DO NOT EDIT)
# --------------------------
if __name__ == "__main__":
    # Use managed SolidWorks session to ensure proper cleanup
    with SolidWorksSession() as sw_session:
        # Create new part document with mmgs units
        part = sw_session.new_document(doc_type="Part", units="mmgs")
        
        # Create base rectangular plate
        base_extrude = sw_part.create_base_rectangular_extrude(
            part,
            length=PLATE_LENGTH,
            width=PLATE_WIDTH,
            height=PLATE_THICKNESS,
            sketch_plane="Front Plane"
        )
        
        # Add 1mm chamfer to outer perimeter edges
        sw_part.add_edge_chamfer(
            part,
            distance=CHAMFER_DISTANCE,
            angle=CHAMFER_ANGLE,
            target_edges="outer_perimeter"
        )
        
        # Add four M6 through holes
        sw_part.add_through_holes(
            part,
            hole_positions=hole_positions,
            diameter=HOLE_DIAMETER,
            sketch_plane="Top Face",
            depth_type="through_all"
        )
        
        # Save SLDPRT file
        sldprt_path = os.path.join(OUTPUT_DIRECTORY, f"{PART_BASE_NAME}.SLDPRT")
        sw_session.save_document(part, sldprt_path, overwrite=True)
        
        # Export STEP file
        step_path = os.path.join(OUTPUT_DIRECTORY, f"{PART_BASE_NAME}.STEP")
        sw_export.export_step(
            part,
            output_path=step_path,
            schema="AP214",
            include_color=True
        )
        
        # Clean up document
        sw_session.close_document(part)
        
        # Print success output
        print("Mounting plate created successfully!")
        print(f"SLDPRT file: {sldprt_path}")
        print(f"STEP file: {step_path}")
