from __future__ import annotations

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("SWAI_PROJECT_ROOT") or getattr(sys, "_MEIPASS", "") or Path.cwd())
VENDORED_SW_SCRIPTS = PROJECT_ROOT / "vendor" / "skills" / "solidworks-automation" / "scripts"
if VENDORED_SW_SCRIPTS.exists() and str(VENDORED_SW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDORED_SW_SCRIPTS))

import os
import sys
import math

# Human approval required before running this script.
# This script performs only SolidWorks automation and writes outputs only to the requested directory.

OUTPUT_DIR = r"C:\Users\Vision\Documents\sw skill 应用化\outputs\temp\generated\70c55ce3614942bc9813f983355fe26d\outputs"
PART_PATH = os.path.join(OUTPUT_DIR, "mounting_plate_120x80x10_M6.SLDPRT")
STEP_PATH = os.path.join(OUTPUT_DIR, "mounting_plate_120x80x10_M6.STEP")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")) if "__file__" in globals() else os.getcwd()
VENDOR_SCRIPTS = os.path.join(REPO_ROOT, "vendor", "skills", "solidworks-automation", "scripts")
if VENDOR_SCRIPTS not in sys.path:
    sys.path.insert(0, VENDOR_SCRIPTS)

from sw_session import SolidWorksSession
import sw_part
import sw_export
import sw_review


def _ensure_output_dir(path):
    requested = os.path.normcase(os.path.abspath(OUTPUT_DIR))
    target = os.path.normcase(os.path.abspath(path))
    if target != requested:
        raise RuntimeError("Refusing to write outside the requested output directory")
    os.makedirs(path, exist_ok=True)


def _try_call(obj, names, *args, **kwargs):
    last_exc = None
    for name in names:
        fn = getattr(obj, name, None)
        if callable(fn):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
    if last_exc:
        raise last_exc
    raise AttributeError("None of the requested methods exist: " + ", ".join(names))


def _new_part(session):
    for name in ("new_part", "create_part", "new_document"):
        fn = getattr(session, name, None)
        if callable(fn):
            try:
                doc = fn()
                if doc is not None:
                    return doc
            except TypeError:
                try:
                    doc = fn("part")
                    if doc is not None:
                        return doc
                except Exception:
                    pass
    sw_app = getattr(session, "sw", None) or getattr(session, "app", None) or getattr(session, "solidworks", None)
    if sw_app is None:
        raise RuntimeError("Could not access SolidWorks application from session")
    try:
        return sw_app.NewPart()
    except Exception:
        template = ""
        return sw_app.NewDocument(template, 0, 0, 0)


def _create_plate_with_api(doc):
    # Units: meters for SolidWorks API dimensions.
    length = 0.120
    width = 0.080
    thickness = 0.010
    hole_dia = 0.0066
    hole_offset_x = 0.015
    hole_offset_y = 0.015
    chamfer = 0.001

    model = doc
    ext = model.Extension
    feat_mgr = model.FeatureManager
    sketch_mgr = model.SketchManager

    # Select Front Plane and sketch centered rectangle.
    selected = ext.SelectByID2("Front Plane", "PLANE", 0, 0, 0, False, 0, None, 0)
    if not selected:
        selected = ext.SelectByID2("前视基准面", "PLANE", 0, 0, 0, False, 0, None, 0)
    if not selected:
        raise RuntimeError("Could not select Front Plane")

    sketch_mgr.InsertSketch(True)
    sketch_mgr.CreateCenterRectangle(0, 0, 0, length / 2.0, width / 2.0, 0)
    sketch_mgr.InsertSketch(True)

    # Extrude mid-plane if possible; fallback to blind.
    try:
        feat_mgr.FeatureExtrusion2(True, False, True, 0, 0, thickness / 2.0, thickness / 2.0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
    except Exception:
        feat_mgr.FeatureExtrusion2(True, False, False, 0, 0, thickness, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)

    # Through holes: sketch on top face at z = +thickness/2, cut through all.
    model.ClearSelection2(True)
    selected = ext.SelectByID2("", "FACE", 0, 0, thickness / 2.0, False, 0, None, 0)
    if not selected:
        # Try selecting by ray from above toward the part.
        selected = ext.SelectByRay(0, 0, thickness, 0, 0, -1, 0.001, 2, False, 0, 0)
    if not selected:
        raise RuntimeError("Could not select top face for hole sketch")

    sketch_mgr.InsertSketch(True)
    pts = [
        (length / 2.0 - hole_offset_x, width / 2.0 - hole_offset_y),
        (-(length / 2.0 - hole_offset_x), width / 2.0 - hole_offset_y),
        (-(length / 2.0 - hole_offset_x), -(width / 2.0 - hole_offset_y)),
        (length / 2.0 - hole_offset_x, -(width / 2.0 - hole_offset_y)),
    ]
    for x, y in pts:
        sketch_mgr.CreateCircleByRadius(x, y, 0, hole_dia / 2.0)
    sketch_mgr.InsertSketch(True)
    feat_mgr.FeatureCut3(True, False, False, 1, 1, thickness * 2.0, thickness * 2.0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False)

    # Apply chamfer to all suitable edges using global edge selection where possible.
    model.ClearSelection2(True)
    try:
        body = model.GetBodies2(0, True)[0]
        edges = body.GetEdges()
        mark = 0
        for edge in edges:
            try:
                edge.Select4(True, None)
            except Exception:
                pass
        try:
            feat_mgr.InsertFeatureChamfer(4, 1, chamfer, chamfer, 0, 0, 0, 0)
        except Exception:
            # Alternative chamfer API signature on some versions.
            feat_mgr.InsertFeatureChamfer(4, 1, chamfer, 0, 0, 0, 0, 0)
    finally:
        model.ClearSelection2(True)

    try:
        model.EditRebuild3()
    except Exception:
        model.ForceRebuild3(False)


def _save_as(doc, path):
    ext = doc.Extension
    errors = 0
    warnings = 0
    try:
        result = ext.SaveAs(path, 0, 1, None, errors, warnings)
        if result is False:
            raise RuntimeError("SaveAs returned False for " + path)
    except Exception:
        try:
            result = doc.SaveAs3(path, 0, 0)
            if result is False:
                raise RuntimeError("SaveAs3 returned False for " + path)
        except Exception:
            result = doc.SaveAs(path)
            if result is False:
                raise RuntimeError("SaveAs returned False for " + path)


def main():
    _ensure_output_dir(OUTPUT_DIR)

    session = SolidWorksSession()
    connect_fn = getattr(session, "connect", None)
    if callable(connect_fn):
        connect_fn()

    doc = _new_part(session)
    if doc is None:
        raise RuntimeError("Failed to create a new SolidWorks part document")

    # Prefer vendored high-level helpers if available; otherwise use direct API with session-created document.
    used_helper = False
    helper_names = ("create_box", "create_rectangular_plate", "make_plate")
    for helper_name in helper_names:
        helper = getattr(sw_part, helper_name, None)
        if callable(helper):
            try:
                helper(doc, length_mm=120, width_mm=80, thickness_mm=10)
                used_helper = True
                break
            except TypeError:
                try:
                    helper(doc, 120, 80, 10)
                    used_helper = True
                    break
                except Exception:
                    pass
            except Exception:
                pass

    if not used_helper:
        _create_plate_with_api(doc)

    try:
        review = getattr(sw_review, "review_active", None)
        if callable(review):
            review(session)
    except Exception:
        pass

    _save_as(doc, PART_PATH)

    exported = False
    for export_name in ("export_step", "export_active_step", "export_active"):
        export_fn = getattr(sw_export, export_name, None)
        if callable(export_fn):
            try:
                export_fn(session, STEP_PATH)
                exported = True
                break
            except TypeError:
                try:
                    export_fn(doc, STEP_PATH)
                    exported = True
                    break
                except Exception:
                    pass
            except Exception:
                pass
    if not exported:
        _save_as(doc, STEP_PATH)

    return {"part": PART_PATH, "step": STEP_PATH}


if __name__ == "__main__":
    main()