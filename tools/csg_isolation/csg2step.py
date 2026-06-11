"""Headless OpenSCAD .csg -> STEP conversion driver.

Run with:  FreeCADCmd csg2step.py <input.csg> <output.step>

Prints a single JSON object (between CSG2STEP_RESULT markers) describing the
outcome, including the stage at which a failure occurred:
  parse | recompute | empty-result | invalid-shape | export | ok
"""

import json
import os
import sys
import time
import traceback


def emit(result):
    sys.stdout.write("\nCSG2STEP_RESULT_BEGIN\n")
    sys.stdout.write(json.dumps(result, indent=1))
    sys.stdout.write("\nCSG2STEP_RESULT_END\n")
    sys.stdout.flush()


def configure_params():
    import FreeCAD
    import shutil

    params = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/OpenSCAD")
    openscad = os.environ.get("CSG2STEP_OPENSCAD") or shutil.which("openscad") or ""
    if openscad:
        params.SetString("openscadexecutable", openscad)
    # tempdir transfer; mech 2 (pipes) needs openscad >= 2021.01 but keeps
    # tempdir default for closest-to-GUI behaviour
    params.SetInt("transfermechanism", 0)
    return {"openscadexecutable": openscad}


def shape_stats(obj):
    s = obj.Shape
    return {
        "label": obj.Label,
        "type": obj.TypeId,
        "isNull": s.isNull(),
        "isValid": (not s.isNull()) and s.isValid(),
        "solids": len(s.Solids),
        "faces": len(s.Faces),
        "volume": s.Volume if not s.isNull() else None,
    }


def main():
    # paths come via env: FreeCADCmd opens positional args as documents,
    # so they cannot be used for script arguments
    infile = os.environ["CSG2STEP_IN"]
    outfile = os.environ["CSG2STEP_OUT"]
    result = {
        "input": infile,
        "output": outfile,
        "stage": None,
        "ok": False,
        "error": None,
        "traceback": None,
        "objects_total": 0,
        "roots": [],
        "timings": {},
    }

    import FreeCAD
    result.update(configure_params())

    t0 = time.time()
    result["stage"] = "parse"
    try:
        import importCSG
        doc = importCSG.open(infile)  # includes doc.recompute()
    except BaseException as e:
        result["error"] = "%s: %s" % (type(e).__name__, e)
        result["traceback"] = traceback.format_exc()
        emit(result)
        return 1
    result["timings"]["import"] = round(time.time() - t0, 3)

    # importCSG.open already recomputes; check for objects in error state
    result["stage"] = "recompute"
    touched = [o.Name for o in doc.Objects if "Touched" in o.State]
    errored = [o.Name for o in doc.Objects if "Invalid" in o.State]
    result["objects_total"] = len(doc.Objects)
    result["objects_touched"] = touched
    result["objects_errored"] = errored

    roots = [o for o in doc.RootObjects if hasattr(o, "Shape")]
    result["stage"] = "empty-result"
    if not roots:
        result["error"] = "document has no root objects with a Shape"
        emit(result)
        return 1
    try:
        result["roots"] = [shape_stats(o) for o in roots]
    except BaseException as e:
        result["error"] = "shape stats failed: %s: %s" % (type(e).__name__, e)
        result["traceback"] = traceback.format_exc()
        emit(result)
        return 1

    bad = [r for r in result["roots"] if r["isNull"] or not r["isValid"]]
    # importCSG leaks intermediate 2D primitives (e.g. circles consumed by a
    # difference/offset) as extra root objects; export only solid roots so the
    # comparison against the openscad reference is apples-to-apples, but
    # record the leak — it is an importer bug in its own right.
    solid_roots = [o for o in roots
                   if not o.Shape.isNull() and len(o.Shape.Solids) > 0]
    result["twoD"] = False
    if solid_roots:
        leaked = [o for o in roots if o not in solid_roots]
    else:
        # genuinely 2D model: the face roots ARE the result, not leaks
        leaked = []
        result["twoD"] = any(
            not o.Shape.isNull() and o.Shape.Faces for o in roots)
    result["leaked_2d_roots"] = [o.Label for o in leaked]
    exportable = solid_roots or [o for o in roots if not o.Shape.isNull()]
    if not exportable:
        result["stage"] = "invalid-shape"
        result["error"] = "all root shapes are null"
        emit(result)
        return 1

    result["stage"] = "export"
    t0 = time.time()
    try:
        import Part
        Part.export(exportable, outfile)
    except BaseException as e:
        result["error"] = "%s: %s" % (type(e).__name__, e)
        result["traceback"] = traceback.format_exc()
        emit(result)
        return 1
    result["timings"]["export"] = round(time.time() - t0, 3)

    # tessellated copy of the same result, for volume/visual comparison
    # against an openscad-rendered reference STL
    stl_out = os.path.splitext(outfile)[0] + ".stl"
    try:
        import Mesh
        if result["twoD"]:
            # 2D result: mesh a 1mm extrusion; validate.py renders the
            # openscad reference through the same linear_extrude wrapper
            import Part
            ext = doc.addObject("Part::Feature", "__stl_2d_extrude")
            ext.Shape = Part.makeCompound(
                [o.Shape.extrude(FreeCAD.Vector(0, 0, 1)) for o in exportable])
            Mesh.export([ext], stl_out)
        else:
            Mesh.export(exportable, stl_out)
        result["stl"] = stl_out
    except BaseException as e:
        result["stl"] = None
        result["stl_error"] = "%s: %s" % (type(e).__name__, e)

    if not os.path.isfile(outfile) or os.path.getsize(outfile) == 0:
        result["error"] = "export produced no file"
        emit(result)
        return 1

    result["stage"] = "ok"
    result["ok"] = True
    if bad:
        # exported, but some shapes were invalid -> flag as suspect
        result["ok"] = "suspect"
        result["error"] = "exported with invalid shapes: %s" % [r["label"] for r in bad]
    result["step_size"] = os.path.getsize(outfile)
    emit(result)
    return 0


# FreeCADCmd executes scripts with __name__ set to the module name, never
# "__main__", so run unconditionally; the runner parses the JSON marker.
main()
