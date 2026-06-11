"""Shape-validity tracer for importCSG conversions.

Run with:  CSG2STEP_IN=<file.csg> FreeCADCmd trace_null.py

Monkeypatches importCSG (no source changes needed — the conversion path is
pure Python) to localize null/invalid-shape problems while the CSG tree is
being built:

  * checkObjShape — reports calls that pass a *list* instead of a feature
    (such calls silently skip the null-shape guard);
  * fuse — before fusing, reports any child whose Shape is null, dumps its
    dependency subtree, and tests whether a recursive recompute
    (obj.recompute(True)) resolves it;
  * after the parse — lists every root/invalid object with face/solid/volume
    stats and each invalid object's direct children.

Typical use: a corpus case fails in run_all.py with a null/invalid shape;
run this on the case, read the first TRACE line that goes null, then carve
out the offending subtree with minimize.py until you have a small repro.
"""

import os
import traceback


def configure_params():
    import FreeCAD
    import shutil

    params = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/OpenSCAD")
    openscad = os.environ.get("CSG2STEP_OPENSCAD") or shutil.which("openscad") or ""
    if openscad:
        params.SetString("openscadexecutable", openscad)
    params.SetInt("transfermechanism", 0)


def state(obj, depth=0, seen=None):
    seen = seen if seen is not None else set()
    pad = "  " * depth
    if not hasattr(obj, "Shape"):
        return f"{pad}{obj!r}  <no Shape attr>\n"
    if obj.Name in seen:
        return f"{pad}{obj.Name} (seen)\n"
    seen.add(obj.Name)
    line = f"{pad}{obj.Name} ({obj.TypeId})  null={obj.Shape.isNull()}\n"
    for sub in obj.OutList:
        line += state(sub, depth + 1, seen)
    return line


def shape_summary(shape):
    if shape.isNull():
        return "null=True"
    return (f"null=False valid={shape.isValid()} solids={len(shape.Solids)}"
            f" faces={len(shape.Faces)} vol={shape.Volume:.1f}")


def main():
    configure_params()
    import importCSG

    orig_check = importCSG.checkObjShape
    orig_fuse = importCSG.fuse

    def traced_check(obj):
        if isinstance(obj, (list, tuple)):
            caller = traceback.extract_stack()[-2]
            print(f"TRACE checkObjShape(LIST) from {caller.name}:{caller.lineno}"
                  f" -> {[getattr(o, 'Name', o) for o in obj]}")
        return orig_check(obj)

    def traced_fuse(lst, name):
        for child in lst:
            if hasattr(child, "Shape") and child.Shape.isNull():
                print(f"TRACE fuse({name}): child {child.Name} ({child.TypeId}) is NULL")
                print(state(child), end="")
                child.recompute(True)
                print(f"TRACE after child.recompute(True): null={child.Shape.isNull()}")
        return orig_fuse(lst, name)

    importCSG.checkObjShape = traced_check
    importCSG.fuse = traced_fuse

    infile = os.environ["CSG2STEP_IN"]
    try:
        doc = importCSG.open(infile)
    except BaseException:
        print("TRACE conversion FAILED:")
        traceback.print_exc()
        return

    solid_roots = [o for o in doc.RootObjects
                   if hasattr(o, "Shape") and not o.Shape.isNull() and o.Shape.Solids]
    vol = sum(o.Shape.Volume for o in solid_roots)
    print(f"TRACE conversion COMPLETED: {len(solid_roots)} solid roots, volume={vol:.1f}")
    for o in doc.RootObjects:
        if not hasattr(o, "Shape"):
            print(f"TRACE root {o.Name}: no Shape attr")
            continue
        print(f"TRACE root {o.Name} ({o.TypeId}) state={o.State} {shape_summary(o.Shape)}")
    for o in doc.Objects:
        if "Invalid" not in o.State:
            continue
        print(f"TRACE INVALID {o.Name} ({o.TypeId})")
        for c in o.OutList:
            if hasattr(c, "Shape"):
                print(f"TRACE   child {c.Name} ({c.TypeId}) {shape_summary(c.Shape)}")


main()
