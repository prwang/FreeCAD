# CSG → STEP conversion: ground-truth validation results

Date: 2026-06-10 · FreeCAD master `165c08f9ff` (headless build, Debian 13 container) ·
Ground truth: OpenSCAD 2021.01 (`openscad -o <name>.ref.stl <name>.csg`)

**Method.** Each `.csg` is converted headlessly via `tools/csg_isolation/run_all.py`
(one `FreeCADCmd` process per file → `.step` + tessellated `.stl` of the solid
roots), then `validate.py` compares the FreeCAD STL against the OpenSCAD-rendered
reference STL: mesh volume by divergence theorem and bounding box.
Tolerances: volume error ≤ 2 % (tessellation noise), bbox component delta ≤ 0.1 mm.

**Summary: 27 / 31 MATCH, 4 FAIL (no conversion produced). Every conversion that
completes produces the correct shape** — the worklist is exactly the 4 crashes.

| # | case | conversion | shape vs ground truth | vol ref (mm³) | vol FreeCAD (mm³) | vol err % | bbox Δ (mm) | leaked 2D roots |
|---|------|-----------|----------------------|--------------:|------------------:|----------:|------------:|:---:|
| 1 | baseline_preview | **FAIL** (fuse: `Null input shape`, importCSG.py:594) | — | 915451.60 (ref OK) | — | — | — | — |
| 2 | batt_box_left_end | ok | MATCH | 8880.83 | 8897.29 | 0.185 | 0.0 | 4 |
| 3 | batt_box_retention_strip | ok | MATCH | 4779.41 | 4782.02 | 0.055 | 0.0 | 0 |
| 4 | batt_box_right_end | ok | MATCH | 7395.51 | 7395.51 | 0.000 | 0.0 | 0 |
| 5 | batt_box_side | ok | MATCH | 16851.07 | 16851.06 | 0.000 | 0.0 | 0 |
| 6 | batt_box_top_bottom | ok | MATCH | 16957.09 | 16957.09 | 0.000 | 0.0 | 0 |
| 7 | case1.scad | ok | MATCH | 295.98 | 296.27 | 0.099 | 0.002 | 2 |
| 8 | case2.scad | ok | MATCH | 295.98 | 296.27 | 0.099 | 0.002 | 2 |
| 9 | case3.scad | ok | MATCH | 295.98 | 296.27 | 0.099 | 0.002 | 0 |
| 10 | caseA.scad | ok | MATCH | 267.35 | 268.64 | 0.481 | 0.002 | 3 |
| 11 | caseB.scad | ok | MATCH | 228.58 | 229.48 | 0.394 | 0.002 | 3 |
| 12 | caseC.scad | ok | MATCH | 228.58 | 229.48 | 0.394 | 0.002 | 3 |
| 13 | caseD.scad | ok | MATCH | 386.37 | 387.64 | 0.330 | 0.0 | 2 |
| 14 | caseE.scad | ok | MATCH | 88.16 | 88.49 | 0.375 | 0.008 | 1 |
| 15 | caseF.scad | **FAIL** (intersection: `no attribute 'Base'`, importCSG.py:671) | — | — | — | — | — | — |
| 16 | caseG1.scad | **FAIL** (same as caseF) | — | — | — | — | — | — |
| 17 | caseG2.scad | ok | MATCH | 417.96 | 419.83 | 0.447 | 0.002 | 3 |
| 18 | caseG3.scad | ok | MATCH | 1262.84 | 1262.93 | 0.007 | 0.0 | 1 |
| 19 | caseG4.scad | **FAIL** (same as caseF) | — | — | — | — | — | — |
| 20 | center_panel_RasPi | ok | MATCH | 10324.02 | 10324.02 | 0.000 | 0.0 | 0 |
| 21 | end_plate_battery_side | ok | MATCH | 18845.03 | 18840.83 | 0.022 | 0.02 | 4 |
| 22 | end_plate_rx_side | ok | MATCH | 22830.04 | 22825.96 | 0.018 | 0.02 | 2 |
| 23 | fiber_mount_plate | ok | MATCH | 1792.74 | 1792.73 | 0.001 | 0.0 | 0 |
| 24 | pa_mount_top | ok | MATCH | 12276.45 | 12276.44 | 0.000 | 0.0 | 0 |
| 25 | rx_panel_lower | ok | MATCH | 37481.52 | 37481.52 | 0.000 | 0.0 | 0 |
| 26 | rx_support_upper | ok | MATCH | 811.98 | 811.97 | 0.002 | 0.0 | 0 |
| 27 | smoke_panel_3d | ok | MATCH | 2336.39 | 2336.32 | 0.003 | 0.0 | 0 |
| 28 | smoke_screw | ok | MATCH | 535.36 | 535.73 | 0.070 | 0.0 | 0 |
| 29 | transformer_mount_bracket | ok | MATCH | 1971.75 | 1971.63 | 0.006 | 0.0 | 0 |
| 30 | wrench55 | ok | MATCH | 1178.04 | 1178.10 | 0.006 | 0.003 | 2 |
| 31 | wrench55_union | ok | MATCH | 1178.04 | 1178.10 | 0.006 | 0.003 | 2 |

Full per-case numbers: `csg_out/validation.json` (volumes, bboxes) and
`csg_out/summary.json` (conversion stages, per-root shape stats, leaked roots).

## Failures (Phase 2 worklist)

1. **caseF / caseG1 / caseG4 — intersection crash.**
   `importCSG.py:671` runs `mycommon.Base.Shape.common(mycommon.Tool.Shape)`
   unconditionally, but `Base`/`Tool` only exist in the exactly-2-children
   branch of `p_intersection_action`. Any `intersection()` with 1 or >2
   children raises `AttributeError`. (caseG2 passes only because its
   intersections happen to have exactly 2 children.)

2. **baseline_preview — null shape in union.**
   `importCSG.py:594` `fuse()` raises `ValueError: Null input shape`: some
   union/group child arrives with a null shape. The file is the corpus's
   heaviest `offset()` user (22 offsets, 24 differences, 4 intersections) —
   the known offset-fillet instability. The OpenSCAD reference for this file
   renders fine (slow: ~3 min CGAL, vol 915 451.6 mm³), so ground truth exists
   for validating a fix.

## Secondary finding — leaked 2D root objects

For 13 of the 27 passing cases, importCSG leaves intermediate 2D primitives
(`circle`, …) as extra *visible root objects* in the document, even though they
were consumed children of `difference`/`intersection`/`offset` nodes in the
.csg tree. They have zero volume but pollute the document (and any naive
export — they initially produced bbox deltas up to 164 mm in this validation
until the harness restricted export to solid roots). This is an importer
structural bug, lower priority than the crashes.

## Notes on comparison fidelity

- Volume errors ≤ 0.5 % everywhere; consistent with tessellation noise plus
  OpenSCAD's polygonal-circle semantics (a `circle($fn=96)` is an inscribed
  96-gon, FreeCAD uses a true circle — e.g. wrench55 bbox x-max 5.86 vs 6.0
  before the 96-gon flat lands on the axis).
- bbox deltas ≤ 0.02 mm on all passing cases.
- No case in this corpus uses `hull()`/`minkowski()`, so the
  external-openscad fallback path is configured but unexercised.
