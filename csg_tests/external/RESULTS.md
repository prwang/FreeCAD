# External corpus — first full run (2026-06-13)

204 cases (see SOURCES.md; compiled with OpenSCAD 2021.01, converted by the
fix-csg importer, validated against openscad-rendered ground truth, 4 GB
memory cap per child process).

## Headline

| | count |
|---|---|
| converted ok | 124 |
| converted but some shape invalid (suspect) | 13 |
| failed (parse / invalid-shape / empty-result / crash) | 67 |
| validated MATCH (volume ≤2 %, bbox ≤0.1 mm) | 78 / 137 |
| validated MISMATCH | 52 / 137 |
| reference not renderable (NO-REF, openscad timeout/OOM-cap/empty) | 7 |

The unit corpus (`csg_tests/`, 35 cases) remains 35/35 MATCH — these are all
*new* defects beyond the eight classes already fixed.

## Priority A — high-leverage: simple constructs, easy to minimize/validate

Each of these is a small upstream-test-corpus file built from primitives;
minimized red/green regressions are cheap.

| case | symptom | suspected area |
|---|---|---|
| `t3d__transform-tests` | vol −73 % | core transform handling (multmatrix/rotate ladder) |
| `t3d__color-names-tests`, `t3d__hex-colors-tests`, `t3d__colored-nodes` | vol −96 %/−91 %/−24 % | `color()` drops most child geometry |
| `t3d__difference-tests`, `t3d__intersection-tests`, `t2d__difference-2d-tests` | vol err 24 %/26 %/20 % | core booleans wrong on multi-child/nested forms |
| `t2d__intersection2-tests`, `jbarr__nodes_graph`, `jbarr__rhombitrihexagon`, `jbarr__routing_tiles` | crash `ValueError: Null input shape` | 2-child boolean with empty operand (eager `.fuse/.common` on empty shape) |
| `t3d__highlight-and-background-modifier`, `t3d__highlight-modifier`, `t2d__highlight-modifier-2d` | vol err 70 %/14 %/6 % | `#`/`%` modifier combinations (follow-up to the `%` fix) |
| `t2d__resize-2d-tests` | crash ZeroDivisionError | `resize()` with zero/auto dims |
| `t3d__resize-tests` | vol err 4×10⁹ % | `resize()` 3D — result essentially unbounded |
| `t3d__rotate_extrude-angle` | crash `not enough values to unpack` | `rotate_extrude(angle=…)` |
| `t3d__rotate_extrude-tests` | crash `KeyError: 'file'` | rotate_extrude grammar assumes file kwarg |
| `t2d__circle-tests` | crash `int('0.1')` | fractional `$fn` |
| `t2d__square-tests`, `t2d__scale2D-tests` | invalid shapes; vol err 1429 % | square/scale 2D degenerate sizes (zero dims) |
| `t3d__sphere-tests`, `t3d__scale3D-tests`, `t3d__linear_extrude-tests`, `t3d__linear_extrude-scale-zero-tests`, `t3d__linear_extrude_invisible-tests`, `ex__linear_extrude` | suspect/invalid shapes; vol err up to 73 % | degenerate primitives (r=0, scale 0, height 0, twist) |
| `t2d__offset-tests` | crash `shape is invalid` | offset() variant we don't cover yet |
| `t2d__polygon-corner-cases`, `t2d__polygon-tests` | vol err 65 %/4 % | polygon() self-touching/multi-path cases |
| `t3d__polyhedron-tests`, `t3d__polyhedron-nonplanar-tests` | vol err 50 %/7×10⁶ % | polyhedron face orientation / non-planar faces |
| `t3d__primitive-inf-tests` | empty document | inf/huge primitive dimensions |
| `t2d__projection-tests`, `t2d__projection-cut-tests`, `t3d__projection-extrude-tests` | vol err 38 %/32 %/4 % | projection()/cut |

## Priority B — environmental / harness-side (not importer geometry bugs)

- **`text()` → 26 failures** (`'NoneType' object has no attribute 'readDXF'`):
  openscad renders the text to DXF fine, but `OpenSCAD2Dgeom.importDXFface`
  goes through Draft's *legacy* python DXF importer, whose `dxfReader`
  library isn't installed headless. Fix direction: use the modern importer
  or fail soft. Hits real-world files (all Prusa parts, Ultimate Box).
- **Companion files missing → 6 failures** (`File does not exist`,
  `FileNotFoundError`): cases importing sibling `.dxf/.dat/.png`; the
  harvest step doesn't copy them. Harness-side fix in fetch_and_compile.py.
- **NO-REF ×7**: openscad itself can't render the reference (timeout, the
  4 GB cap, or genuinely empty result, e.g. `nullspace-*`). For the empty
  ones, FreeCAD producing an empty document would be the *correct* outcome.

## Unknown / postponed (complicated; cause not yet isolated)

- `dactyl__dactyl-top-right` — 4.5 MB generated tree; fuse fails
  (self-intersecting wire / unorientable). Needs minimization first.
- `ex__module_recursion`, `t3d__module-recursion` (−31 %) — deep recursion,
  unorientable fuse input.
- `roundany__*` (9 cases) — every Round-Anything example imports as an
  EMPTY document. Probably one shared root cause in polygon()-heavy input;
  worth minimizing early since it's a whole-library wipeout.
- hull/minkowski null results: `t2d__hull2-tests`, `t2d__minkowski2-*`,
  `t3d__minkowski3-erosion`, `t3d__nullspace-minkowski*`,
  `t2d__control-hull-dimension`, `t3d__minkowski3-difference-test` (hang).
  The external-openscad delegation path was known-unexercised; now we have
  cases. Needs dedicated investigation.
- `threads__threads`, `keyv2__plate_generation`,
  `gridfin__gridfinity-spiral-vase`, `jbarr__heart_purse` — convert to
  all-null roots after long boolean grinds.
- Borderline mismatches 2–4 % (`cylinder-diameter-tests`, `child-tests`,
  `candleStand`, keyv2 trio, …) — possibly tessellation-tolerance artifacts
  of the volume comparison rather than real defects; revisit after the
  Priority A fixes move the noise floor.

## Reproduce

```sh
python3 csg_tests/external/fetch_and_compile.py
python3 src/Mod/OpenSCAD/csg_isolation/run_all.py  --tests csg_external/csg --out csg_external/out
python3 src/Mod/OpenSCAD/csg_isolation/validate.py --tests csg_external/csg --out csg_external/out
```
