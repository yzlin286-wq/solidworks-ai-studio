from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

from vendor.skills.solidworks_automation.scripts import SolidWorksSession
from vendor.skills.solidworks_automation.scripts.sw_part import (
    create_new_part,
    get_reference_plane,
    create_sketch,
    create_rectangle,
    add_dimension,
    exit_sketch,
    extrude_boss,
    get_top_face_of_extrusion,
    create_point,
    create_simple_hole,
    get_outer_perimeter_edges,
    create_chamfer
)
from vendor.skills.solidworks_automation.scripts.sw_export import export_step
from vendor.skills.solidworks_automation.scripts import solidworks_save_document
import os

# USER MUST SET THIS TO YOUR SELECTED WORKSPACE OUTPUT DIRECTORY
OUTPUT_DIR = r"REPLACE_WITH_USER_WORKSPACE_OUTPUT_PATH"
PART_FILENAME = "MountingPlate_120x80x10"

# Part dimensions (all units: mm)
PLATE_LENGTH = 120.0
PLATE_WIDTH = 80.0
PLATE_THICKNESS = 10.0
M6_HOLE_DIAMETER = 6.0
HOLE_CENTER_OFFSET = 10.0  # Offset from plate edges to hole center
CHAMFER_SIZE = 1.0
CHAMFER_ANGLE = 45.0


def main():
    # Validate output directory exists before starting SolidWorks session
    if not os.path.isdir(OUTPUT_DIR):
        raise NotADirectoryError(
            f"Output directory does not exist: {OUTPUT_DIR}. Please update OUTPUT_DIR to a valid workspace path."
        )

    # Initialize SolidWorks session (automatically cleans up on exit
    with SolidWorksSession() as sw_session:
        # Create new empty part document
        part_document = create_new_part(sw_session)

        # Step 1: Create base plate sketch on Front Plane
        front_plane = get_reference_plane(part_document, "Front Plane")
        base_sketch = create_sketch(part_document, front_plane, "BasePlateSketch")

        # Draw 120x80 rectangle with origin at lower-left corner
        create_rectangle(base_sketch, 0.0, 0.0, PLATE_LENGTH, PLATE_WIDTH)
        # Add dimensional constraints to fully define the sketch
        add_dimension(base_sketch, "PlateLength", PLATE_LENGTH)
        add_dimension(base_sketch, "PlateWidth", PLATE_WIDTH)
        exit_sketch(base_sketch)

        # Step 2: Extrude base sketch to 10mm thickness
        extrude_boss(
            part_document,
            feature_name="BasePlateExtrusion",
            sketch=base_sketch,
            depth=PLATE_THICKNESS,
            direction=1  # Extrude normal to sketch plane
        )

        # Step 3: Create hole center sketch on top face of base plate
        top_plate_face = get_top_face_of_extrusion(part_document, "BasePlateExtrusion")
        hole_sketch = create_sketch(part_document, top_plate_face, "M6HoleCenters")

        # Define 4 hole center positions (10mm offset from each corner)
        hole_centers = [
            (HOLE_CENTER_OFFSET, HOLE_CENTER_OFFSET),
            (PLATE_LENGTH - HOLE_CENTER_OFFSET, HOLE_CENTER_OFFSET),
            (PLATE_LENGTH - HOLE_CENTER_OFFSET, PLATE_WIDTH - HOLE_CENTER_OFFSET),
            (HOLE_CENTER_OFFSET, PLATE_WIDTH - HOLE_CENTER_OFFSET)
        ]
        for x_coord, y_coord in hole_centers:
            create_point(hole_sketch, x_coord, y_coord)
        exit_sketch(hole_sketch)

        # Step 4: Create M6 through holes
        create_simple_hole(
            part_document,
            feature_name="M6ThroughHoles",
            sketch=hole_sketch,
            diameter=M6_HOLE_DIAMETER,
            end_condition="Through All"
        )

        # Step 5: Add 1mm chamfers to outer plate edges
        outer_perimeter_edges = get_outer_perimeter_edges(part_document, "BasePlateExtrusion")
        create_chamfer(
            part_document,
            feature_name="OuterEdgeChamfers",
            selected_edges=outer_perimeter_edges,
            distance1=CHAMFER_SIZE,
            angle=CHAMFER_ANGLE,
            chamfer_type="Distance Angle"
        )

        # Step 6: Save as SLDPRT
        sldprt_save_path = os.path.join(OUTPUT_DIR, f"{PART_FILENAME}.SLDPRT")
        solidworks_save_document(part_document, sldprt_save_path)

        # Step 7: Export as STEP (AP214 format for mechanical interoperability)
        step_export_path = os.path.join(OUTPUT_DIR, f"{PART_FILENAME}.step")
        export_step(part_document, step_export_path, export_format="AP214")

        print(f"Mounting plate creation complete:")
        print(f"  SLDPRT: {sldprt_save_path}")
        print(f"  STEP: {step_export_path}")


if __name__ == "__main__":
    main()
