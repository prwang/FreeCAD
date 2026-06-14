# CURRENT BUG — A3#9 projection()

## Observation
- Family: t2d__projection-cut-tests, t2d__projection-tests, ex__projection.
- The plan flagged "projection-cut ~32 % off / projection-tests 38 %".
- Repro probes (analytic):
  - cut=true, centered cube → slice z=0 = 10×10, **area 100.0000** (exact).
  - cut=true, sphere r=10 $fn=64 → equator circle, **area 314.1497**
    (vs 100π=314.159, 0.003 % = $fn faceting).
  - cut=true, 2D square([10,10]) → **area 100.0000** (coplanar, exact).
  - cut=true, cube translated to z=5 (slice misses it) → **area 0** (exact).
  - cut=false, centered cube → **2 roots**: a stray
    `xy_plane_used_for_projection` (Plane, **area 100**) + an empty
    `projection` placeholder.

## Hypotheses (each independently testable)
- H1: cut=true is broken (the "32 %" is a real importer error in the slice).
- H2: the "32 %"/"38 %" was $fn faceting and/or a missing companion file
  (`projection.stl` in ex__projection), not an importCSG geometry defect, and
  cut=true is actually correct.
- H3: cut=false leaks the helper plane `xy_plane_used_for_projection` as an
  orphan document root because the plane is created unconditionally
  (importCSG.py p_projection_action lines ~1593-1599) but only consumed
  (added to `obj.Shapes`) in the cut=true branch.
- H4: true projection (cut=false shadow/silhouette) is missing geometry — but
  it is an explicit `usePlaceholderForUnsupported` placeholder by design, and
  the silhouette has no clean analytic/OCC target.

## Evidence log
- cut=true probes above are all exact (100, 100, 0) or faceting-only (sphere).
  → **H1 REJECTED, H2 ACCEPTED** (cut=true is correct; residual error was
  faceting / the missing `projection.stl` companion, not importCSG).
- cut=false probe shows roots=2 incl. `xy_plane_used_for_projection` area 100.
  In the cut=true probe roots=1 (the plane is a child of MultiCommon, not a
  root). `placeholder()` wraps the children, so the children are consumed; only
  the plane leaks. → **H3 ACCEPTED**.
- True projection: no OCC primitive; OpenSCAD unions all cross-sections. No
  clean analytic target; existing design intentionally emits a placeholder.
  → **H4: out of minimal scope — leave the placeholder; UNKNOWN/postponed.**

## Verdict
- **H3 ACCEPTED** (and H2). H1 REJECTED. H4 honestly postponed.
- Fix: build the `xy_plane_used_for_projection` plane (and the bbox work that
  only sizes it) **inside the cut=true branch**, so the cut=false path no
  longer leaks a stray plane root. cut=true geometry is unchanged; true
  projection stays a placeholder.
- Analytic expected: `projection(cut=false) cube(...)` imports with **no**
  `xy_plane_used_for_projection` root (only the empty placeholder); cut=true
  slice areas unchanged (cube=100, empty-slice=0).
