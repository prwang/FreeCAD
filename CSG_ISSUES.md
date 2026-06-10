# OpenSCAD CSG → STEP conversion: known issues & work state

Working notes for the csg-conversion hardening effort (branch `fix-csg`).
Baseline commit = headless isolation harness + ground-truth validation,
NO importer fixes yet. This file is the context handoff: everything needed
to continue Phase 2 (the fixes) is here or referenced from here.

## Environment (container)

- LXC container `deb13-dev` (Debian 13/trixie — its occt 7.8.1 matches the
  repo pixi pin; Ubuntu 24.04 host occt 7.6.3 does not). Repo mounted at
  `/work/FreeCAD`:
  `lxc config device add deb13-dev freecad disk source=<repo> path=/work/FreeCAD shift=true`
- apt deps (stock only): git cmake ninja-build g++ swig python3-dev
  libocct-\*-dev qt6-base-dev qt6-tools-dev libboost-\*-dev libxerces-c-dev
  libeigen3-dev libyaml-cpp-dev pybind11-dev libfmt-dev zlib1g-dev
  libfreetype-dev libharfbuzz-dev libvtk9-dev libhdf5-dev libmedc-dev
  python3-ply python3-numpy openscad python3-pyside6.{qtcore,qtgui,qtwidgets}
  pyside6-tools
- Ground truth renderer: `/usr/bin/openscad` (OpenSCAD 2021.01).

## Build (headless, no GUI)

- `build/headless`, Release, Ninja, `BUILD_GUI=OFF`,
  `ENABLE_DEVELOPER_TESTS=OFF`; module set per inter-module deps:
  OPENSCAD→DRAFT→TECHDRAW→{SPREADSHEET,MEASURE}, IMPORT→PART_DESIGN,
  BUILD_MESH_PART=ON (OpenSCADUtils.py imports MeshPart) → bundled SMESH → VTK.
- `cMake/FreeCAD_Helpers/SetupQt.cmake` carries two headless-build fixes
  (LinguistTools always; Qt Gui+Widgets when TechDraw without GUI). Do NOT
  upstream yet (user hold).
- Runtime shims in the **build dir only** (regenerate if build dir is wiped;
  recipes in cMake/FreeCAD_Helpers/SetupShibokenAndPyside.cmake:84-104):
  - `build/headless/Ext/PySide/{__init__,QtCore,QtGui,QtWidgets}.py` →
    re-export PySide6 (Draft imports PySide unconditionally).
  - `build/headless/Mod/Draft/Draft_rc.py` ←
    `pyside6-rcc src/Mod/Draft/Resources/Draft.qrc -o ...`.
- FreeCADCmd gotchas: scripts never run with `__name__ == "__main__"`;
  positional args are opened as documents → the harness passes paths via env.

## Harness — `tools/csg_isolation/`

```
# convert all 31 cases (one FreeCADCmd process per file):
lxc exec deb13-dev -- python3 /work/FreeCAD/tools/csg_isolation/run_all.py --timeout 60
# validate against openscad-rendered references (volume + bbox):
lxc exec deb13-dev -- python3 /work/FreeCAD/tools/csg_isolation/validate.py --timeout 120
```

- `csg2step.py` — runs under FreeCADCmd, env `CSG2STEP_IN`/`CSG2STEP_OUT`;
  `importCSG.open()` → exports STEP + tessellated STL of the **solid roots
  only** (see issue 3); emits JSON record (stage, per-root shape stats,
  leaked roots) between `CSG2STEP_RESULT_BEGIN/END` markers.
- `run_all.py` — drives the corpus, writes `csg_out/summary.json` + logs.
- `validate.py` — pure python; renders `csg_out/<name>.ref.stl` via openscad
  (cached by mtime; baseline_preview needs ~3 min, raise `--timeout`),
  compares volume (divergence theorem) and bbox; writes
  `csg_out/validation.json`. Fixed thresholds for now: vol ≤ 2 %,
  bbox ≤ 0.1 mm (could be tightened to a per-case analytic bound
  `A_curved·d/V + (2π/$fn)²/6` later).
- Corpus: `csg_tests/*.csg` (31 files); results table `csg_tests/test_result.md`.

## Baseline status (corpus, master 165c08f9ff + harness)

27/31 convert AND match OpenSCAD ground truth (vol err ≤ 0.5 %, bbox Δ ≤
0.02 mm). 4 files fail; per-case table in `csg_tests/test_result.md`.
Corpus uses no hull()/minkowski() (that external-openscad path is configured
in csg2step.py but unexercised).

---

## Issue 1 — intersection() crash for ≠ 2 children  [NOT FIXED]

**Affected:** caseF.scad, caseG1.scad, caseG4.scad (each has a 3-child
`intersection()`; caseG2 passes because all of its intersections have
exactly 2 children — verified by brace-counting the .csg trees).

**Symptom:** `AttributeError: 'Part.Feature' object has no attribute 'Base'`
at `src/Mod/OpenSCAD/importCSG.py:671`, stage=parse.

**Cause:** `p_intersection_action` (importCSG.py:645-673) builds a different
feature per child count, then runs the eager shape computation
unconditionally after the ladder:

| children | builds                              | has .Base/.Tool |
|----------|-------------------------------------|-----------------|
| > 2      | Part::MultiCommon (.Shapes)         | no              |
| == 2     | Part::Common (.Base/.Tool)          | yes             |
| == 1     | passthrough child feature           | generally no    |
| == 0     | placeholder group                   | no              |

```python
mycommon.Shape = mycommon.Base.Shape.common(mycommon.Tool.Shape)  # :671
```

Only the 2-child branch can satisfy that line. The eager compute exists so
enclosing parser actions (multmatrix/linear_extrude/...) can read `.Shape`
before any document recompute.

**Evidence the line is misplaced, not fundamental:** `fuse()` (:571) solves
the identical problem correctly — its eager
`myfuse.Shape = myfuse.Base.Shape.fuse(...)` (:594) is *inside* the 2-child
branch only. `p_difference_action` (:617) has no eager compute at all and
works.

**Fix plan:** mirror fuse(): move the eager compute into the branches —
2-child keeps the current line inside the branch; >2-child folds
`reduce(lambda a, b: a.common(b.Shape), ...)` over `.Shapes` (or
`shapes[0].Shape.common([s.Shape for s in rest])`); 1-child and 0-child get
no assignment. Gate: caseF/G1/G4 must MATCH ground truth via validate.py,
zero regressions in the other 28.

## Issue 2 — union/group child with null shape  [NOT FIXED, not yet localized]

**Affected:** baseline_preview (the corpus's heaviest offset() user:
22 offset, 24 difference, 4 intersection nodes).

**Symptom:** `ValueError: Null input shape` from
`myfuse.Base.Shape.fuse(myfuse.Tool.Shape)` at importCSG.py:594, stage=parse.

**State of knowledge:** some union/group child arrives with a null Shape —
suspected 2D offset() chain producing an empty/null intermediate (the known
offset-fillet instability). Ground truth exists: the openscad reference
renders fine (~3 min CGAL; vol 915 451.6 mm³, `csg_out/baseline_preview.ref.stl`).

**Next step:** wrap the parser actions (esp. `p_offset_action`, fuse inputs)
with a per-node shape-validity tracer to localize which child goes null;
minimize the failing subtree to a small .csg repro; then fix root cause.

## Issue 3 — leaked 2D intermediate objects as document roots  [WORKAROUND in harness]

In 13 of 27 passing cases, importCSG leaves intermediate 2D primitives
(`circle`, ...) as extra *visible root objects*, although they were consumed
children of difference/intersection/offset nodes in the .csg. Zero volume,
but they pollute the document and any naive export — they produced bbox
errors up to 164 mm in validation until `csg2step.py` was changed to export
only roots with `len(Shape.Solids) > 0` (leak recorded as `leaked_2d_roots`
in summary.json). Importer-side fix (parent/consume or delete the
intermediates) is lower priority than the crashes.

## Non-issue — OpenSCAD polygonal circle semantics

OpenSCAD circles ARE inscribed n-gons (`$fn`/`$fa`/`$fs`), FreeCAD builds true
circles. Expected discrepancy: relative area/volume deficit ≈ (2π/n)²/6
(0.07 % at $fn=96), radial sag r(1−cos(π/n)) (verified: wrench55's 0.003 mm
bbox delta). Within tolerance everywhere; do not "fix".

## Phase 2 order of work

1. Issue 1 (intersection branches) — smallest, fully understood.
2. Issue 2 (null-shape tracing in baseline_preview).
3. Re-run `run_all.py` + `validate.py` after every change (regression gate).
4. Issue 3 (leaked 2D roots) — after the crashes.
5. NOT in scope: upstreaming SetupQt.cmake fixes (explicit hold),
   hull/minkowski coverage.
