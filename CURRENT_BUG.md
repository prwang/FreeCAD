# CURRENT_BUG — A6: resize() negative newsize component mishandled

## Observation
- **Symptom:** `resize([-5,0,0]) cube([1,1,1])` imports as a mirrored/scaled
  solid of volume **5** (factor −5 on X), but OpenSCAD renders it as the original
  unit cube, volume **1** — a newsize ≤ 0 leaves that axis unchanged.
- **Repro:** `/tmp/rv/A.scad` / `.csg` (`resize(newsize=[-5,0,0], auto=[0,0,0])`).
- **Evidence (OpenSCAD render vs FreeCAD import):** OpenSCAD STL volume = 1.0;
  FreeCAD `_taper`... no — FreeCAD `p_resize_action` factor = −5 → vol 5.0.
- **Corpus impact:** a contributor (alongside the UNKNOWN auto case) to
  `t3d__resize-tests` residual; the pink color group has two `[-5,0,0]` cubes.

## Hypotheses
- **H1 — the zero-guard is an exact string compare that misses negatives.**
  `p_resize_action`: `if new_size[r] == '0': new_size[r] = str(old_size[r])`. A
  negative value formats as e.g. `'-5'`, never equals `'0'`, so it falls through
  to `factor = float('-5')/old = -5`. Testable: a positive resize works, a
  negative one scales by the negative ratio.
- **H2 — OpenSCAD mirrors on negative newsize** (volume 5, oriented flip).
  Testable: render OpenSCAD and read the actual volume/bbox.

## Evidence log
- OpenSCAD render of `resize([-5,0,0]) cube(1)` → volume **1.0** (axis unchanged,
  NOT a mirror) — H2 REJECTED.
- FreeCAD import → volume **5.0** (factor −5).

## Verdict
- **H1 ACCEPTED, H2 REJECTED.** OpenSCAD leaves an axis with newsize ≤ 0
  unchanged (same as the existing == 0 case); FreeCAD's exact-string `== '0'`
  guard misses negatives and applies a negative scale factor.
- Fix: replace the `new_size[r] == '0'` guard with a numeric
  `float(new_size[r]) <= 0` test (covers '0', '0.0', and negatives) → set that
  axis to `old_size[r]` so its factor becomes 1.0 (unchanged).
