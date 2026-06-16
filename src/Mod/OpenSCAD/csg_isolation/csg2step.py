"""Headless OpenSCAD .csg -> STEP conversion driver.

Paths come via the environment (FreeCADCmd treats positional args as documents
to open, so they cannot be script arguments):
  CSG2STEP_IN   input .csg          CSG2STEP_OUT   output .step
  CSG2STEP_OPENSCAD  openscad bin (optional, only for text()/external imports)
  CSG2STEP_HUMAN     set -> print a friendly human summary instead of the JSON
                     marker, and skip the validation-only STL sidecar.

Default (machine) mode prints a single JSON object between CSG2STEP_RESULT
markers describing the outcome, including the stage at which a failure occurred:
  parse | recompute | empty-result | invalid-shape | export | ok
This is the contract run_all.py parses; do not change it. The end-user entry
point is the csg2step.sh wrapper, which runs this in CSG2STEP_HUMAN mode.
"""

import json
import os
import re
import sys
import time
import traceback


def friendly_message(error, tb):
    """Classify a failure as ('unsupported', msg) [an xfail: not an importer
    bug, just a feature this headless path cannot serve] or ('error', None)
    [a genuine conversion defect]. Matches the known environmental signatures
    surfaced by the corpus sweep."""
    blob = (error or "") + "\n" + (tb or "")
    if "readDXF" in blob:
        return ("unsupported",
                "this model uses text() or an imported DXF, which needs "
                "FreeCAD's Draft module (not available in this headless build)")
    if "No such file or directory" in blob or "File does not exist" in blob:
        m = re.search(r"No such file or directory: '([^']+)'", blob)
        what = " ('%s')" % m.group(1) if m else ""
        return ("unsupported",
                "this model imports an external file%s (import()/surface()/"
                "include) that was not found next to the .csg" % what)
    return ("error", None)


def _classify(result):
    if result.get("category") is not None:
        return
    ok = result.get("ok")
    if ok is True:
        result["category"] = "ok"
    elif ok == "suspect":
        result["category"] = "suspect"
    else:
        cat, msg = friendly_message(result.get("error"), result.get("traceback"))
        result["category"] = cat
        if msg:
            result["message"] = msg


def _emit_json(result):
    sys.stdout.write("\nCSG2STEP_RESULT_BEGIN\n")
    sys.stdout.write(json.dumps(result, indent=1))
    sys.stdout.write("\nCSG2STEP_RESULT_END\n")
    sys.stdout.flush()


def _emit_human(result):
    cat = result["category"]
    lines = []
    if cat in ("ok", "suspect"):
        roots = result.get("roots", [])
        nsol = sum(r.get("solids", 0) for r in roots)
        vol = sum((r.get("volume") or 0) for r in roots)
        what = "%s  (%d solid%s, volume %.4g)" % (
            result["output"], nsol, "" if nsol == 1 else "s", vol)
        if cat == "suspect":
            lines.append("! wrote %s" % what)
            lines.append("  warning: some shapes are geometrically invalid: %s"
                         % result.get("error"))
        else:
            lines.append("OK wrote %s" % what)
    elif cat == "unsupported":
        lines.append("SKIP %s" % result["input"])
        lines.append("  unsupported: %s" % result.get("message"))
    else:
        lines.append("FAIL %s" % result["input"])
        lines.append("  conversion failed at stage '%s': %s"
                     % (result.get("stage"), result.get("error")))
    sys.stdout.write("\nCSG2STEP_HUMAN_BEGIN\n")
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.write("CSG2STEP_HUMAN_END\n")
    sys.stdout.write("CSG2STEP_STATUS=%s\n" % cat)
    sys.stdout.flush()


def emit(result):
    _classify(result)
    if os.environ.get("CSG2STEP_HUMAN"):
        _emit_human(result)
    else:
        _emit_json(result)


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
    # against an openscad-rendered reference STL. Pure validation scaffolding:
    # skip it for end users (CSG2STEP_HUMAN) -- they only want the STEP, and
    # the OCC threaded STL mesher is where the few mesh-only segfaults live.
    stl_out = os.path.splitext(outfile)[0] + ".stl"
    if os.environ.get("CSG2STEP_HUMAN"):
        result["stl"] = None
    else:
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
