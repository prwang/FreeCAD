# csg_isolation — offline OpenSCAD CSG conversion & validation harness

A standalone, headless pipeline that exercises FreeCAD's OpenSCAD importer
(`src/Mod/OpenSCAD/importCSG.py`) completely outside the GUI: it converts a
corpus of `.csg` files to STEP, tessellates the results, and validates them
**quantitatively against geometry rendered by OpenSCAD itself** (volume via
the divergence theorem + bounding box). "It didn't crash" is not a pass —
only `MATCH` against OpenSCAD ground truth is.

The entire conversion path is Python (`Mod/OpenSCAD/*.py`), so importer
changes need a `ninja OpenSCAD` (file copy) but **no rebuild**, and all
diagnosis can be done by monkeypatching, without touching the source tree.

```
corpus/*.csg  --(csg2step.py under FreeCADCmd, 1 process/file)-->  csg_out/<name>.step + .stl
corpus/*.csg  --(openscad -o)------------------------------------>  csg_out/<name>.ref.stl
              --(validate.py: volume + bbox compare)------------->  csg_out/validation.json
```

## Deployment

The harness lives at `src/Mod/OpenSCAD/csg_isolation/` and is wired into the
module's CMake (`fc_copy_sources` + `INSTALL` rules in
`src/Mod/OpenSCAD/CMakeLists.txt`), so it ships at
`<prefix>/Mod/OpenSCAD/csg_isolation/` in **every** package format — all
packaging flows (downstream Debian/Ubuntu debs, the in-tree Fedora spec,
conda/rattler, Windows NSIS and pixi bundles) package the CMake install tree
wholesale. `run_all.py` locates `FreeCADCmd` relative to that layout
(`<prefix>/bin` is a sibling of `<prefix>/Mod`), falling back to
`$FREECADCMD` and `$PATH` (which covers the Debian `/usr/bin` symlink and
the conda `freecadcmd` rename). Output goes to `./csg_out` under the current
working directory — the install tree is read-only.

On a deployed system the conversion flow is exactly:

```sh
python3 <prefix>/Mod/OpenSCAD/csg_isolation/run_all.py             # bundled corpus
python3 <prefix>/Mod/OpenSCAD/csg_isolation/validate.py            # needs openscad
python3 <prefix>/Mod/OpenSCAD/csg_isolation/run_all.py my/*.csg    # your own files
```

Packaged builds are full GUI builds: the `Ext/PySide` redirect and
`Mod/Draft/Draft_rc.py` are generated and installed by the normal build, so
none of the headless-build shims below are needed at deployment time.

## The bundled corpus — `corpus/`

Deliberately **minimal**: one hand-written `.csg` per fixed importer-defect
class, each verified to FAIL the original importer and MATCH ground truth
with the fixes (the red run against the pre-fix importer: 2 × FAIL@parse,
2 × MISMATCH at 12.5 % / 5.2 % volume error):

| case | defect it guards (numbering below) |
|---|---|
| `intersection_three_children.csg` | 1 — `intersection()` ≠ 2 children crash |
| `lazy_offset_chain.csg` | 2 — null-shape crash through lazy offset/extrude chains |
| `background_modifier.csg` | 4 — `%` subtree must be excluded from the result |
| `offset_fillet_closing.csg` | 6 — 2D fragmentation silently losing `offset` fillets |

Defects 3, 5, 7 and 8 are guarded by unit tests (`OpenSCADTest`) and by the
development corpus. That larger corpus (31+ real-world cases in `csg_tests/`
at the repo root) is intentionally **not** shipped; point `--tests` at it
when working in the repo.

## Prerequisites (development container; none apply to deployed packages)

* Headless FreeCAD build (`build/headless`, `BUILD_GUI=OFF`). Two
  `cMake/FreeCAD_Helpers/SetupQt.cmake` fixes in this branch are required to
  configure such a build (LinguistTools always requested; Qt Gui+Widgets
  requested when TechDraw is built without GUI). Module set:
  OPENSCAD→DRAFT→TECHDRAW→{SPREADSHEET,MEASURE}, IMPORT→PART_DESIGN,
  `BUILD_MESH_PART=ON`.
* Two runtime shims in the **build dir only** (regenerate after wiping it;
  recipes in `cMake/FreeCAD_Helpers/SetupShibokenAndPyside.cmake:84-104`):
  * `build/headless/Ext/PySide/{__init__,QtCore,QtGui,QtWidgets}.py` —
    re-export PySide6 (Draft imports PySide unconditionally);
  * `build/headless/Mod/Draft/Draft_rc.py` — generate with
    `pyside6-rcc src/Mod/Draft/Resources/Draft.qrc -o ...`.
* `openscad` (ground-truth renderer; also used by importCSG for `.scad`
  input and the hull/minkowski path). Discovery order:
  `$CSG2STEP_OPENSCAD`, `$PATH`, then the standard Windows install dirs;
  or pass `validate.py --openscad`.

FreeCADCmd gotchas the harness already works around: scripts never run with
`__name__ == "__main__"`, and positional arguments are opened as documents —
so all scripts take their input via **environment variables**.

## Usage

```sh
HARNESS=build/headless/Mod/OpenSCAD/csg_isolation   # or source/install dir

# convert the bundled corpus (one FreeCADCmd subprocess per file):
python3 $HARNESS/run_all.py --timeout 120

# validate every conversion against an openscad-rendered reference:
python3 $HARNESS/validate.py --timeout 300

# the full development corpus / single cases:
python3 $HARNESS/run_all.py  --tests csg_tests --timeout 120
python3 $HARNESS/validate.py --tests csg_tests --timeout 300
python3 $HARNESS/run_all.py  csg_tests/caseF.scad.csg
python3 $HARNESS/validate.py --tests csg_tests caseF.scad
```

Always run `run_all.py` before `validate.py` (same `--out`): validation
reads `csg_out/summary.json` to know which results are 2D (see below).

## Components

| file | role |
|---|---|
| `csg2step.py` | runs under `FreeCADCmd`; env `CSG2STEP_IN`/`CSG2STEP_OUT`. Sets OpenSCAD prefs headlessly, `importCSG.open()`, sanity-checks every root shape, exports STEP + STL, emits one JSON record between `CSG2STEP_RESULT_BEGIN/END` markers. |
| `run_all.py` | drives the corpus, one subprocess per file (crash/hang isolation, per-file `--timeout`); writes `csg_out/summary.json` + per-case `.log`. |
| `validate.py` | pure python, no FreeCAD; renders `<name>.ref.stl` with openscad (cached by mtime), compares volume (divergence theorem) and bbox of both STLs. Thresholds: `--vol-tol` 2 %, `--bbox-tol` 0.1 mm. Writes `csg_out/validation.json`. |
| `trace_null.py` | diagnostic: monkeypatches `importCSG.checkObjShape`/`fuse` to localize null/invalid shapes while the tree is built; dumps root/invalid object stats after the parse. |
| `minimize.py` | diagnostic: brace-aware `.csg` subtree splitter for bisecting a failing case down to a minimal repro (see workflow below). |

### Result records

`summary.json` (per case, `result` field): `stage` ∈ `parse | recompute |
empty-result | invalid-shape | export | ok | crash | timeout`; `ok` ∈
`true | "suspect" | false` (suspect = exported but some shape invalid);
per-root `{label, type, isNull, isValid, solids, faces, volume}`;
`leaked_2d_roots` (importer left consumed 2D intermediates as roots);
`twoD` (result has faces but no solids); timings.

`validation.json` (per case): `status` ∈ `MATCH | MISMATCH | NO-CONVERSION |
NO-REF`, `vol_ref`, `vol_fc`, `vol_err_pct`, `bbox_max_delta`.

### 2D models

OpenSCAD cannot export 2D geometry to STL, so 2D cases are compared as
**1 mm extrusions on both sides**: `csg2step.py` meshes
`shape.extrude((0,0,1))` of the face roots and flags the record `twoD`;
`validate.py` sees the flag and renders the reference through a generated
`linear_extrude(height = 1) { <original csg> }` wrapper
(`csg_out/<name>.2dref.csg`). Volume comparison then equals area comparison.

## Development corpus — `csg_tests/` (repo root, not shipped)

* `*.csg` — what the harness runs. `.csg` is OpenSCAD's compiled AST (all
  arguments explicit, constants folded); it is valid OpenSCAD source, so
  small repros can be written by hand.
* `*.scad` — sources for the generated `.csg` (`openscad -o x.csg x.scad`).
* `test_truss{,_deMorgan}` — 2D truss profile with `offset(-r) offset(+r)`
  fillets; the direct-union and the De-Morgan-rewritten variant must both
  import as ONE clean region face. `*_3d` variants wrap the same models in
  `linear_extrude(height = 1)` for STL-level validation.
* `test_result.md` — human-readable result table snapshots.

Expected, tolerated deviation: OpenSCAD circles are inscribed n-gons
(`$fn`), FreeCAD builds true circles when `$fn >= useMaxFN`; relative
area/volume deficit ≈ `(2π/n)²/6` (0.07 % at `$fn=96`) — within the 2 %
volume tolerance. Do not "fix" this.

## Debugging workflow

1. `run_all.py` flags a case (`FAIL@stage` / `SUSPECT` / validation
   `MISMATCH`). Read `csg_out/<name>.log`.
2. `CSG2STEP_IN=csg_tests/<name>.csg FreeCADCmd src/Mod/OpenSCAD/csg_isolation/trace_null.py`
   — find the first object that goes null/invalid and its subtree.
3. Bisect: `python3 src/Mod/OpenSCAD/csg_isolation/minimize.py <file.csg> /tmp/mini 0`
   splits the node at path `0` (use dotted paths like `0.2` to go deeper)
   into one file per child subtree; re-run `csg2step.py` on each, keep the
   smallest failing one, repeat. Hand-simplify the survivor into a unit
   fixture.
4. For OCC-level crashes (SIGSEGV inside a recompute): capture the input
   shape of the crashing feature to a `.brep` from a `checkObjShape`
   monkeypatch hook, then reproduce on the loaded brep in a tiny
   FreeCADCmd script — this isolates the kernel call from the importer.
5. Fix the importer; add a **red/green-verified** regression to
   `src/Mod/OpenSCAD/OpenSCADTest/app/test_importCSG.py` (verify the test
   fails on the unfixed code: `git stash push src/Mod/OpenSCAD/<file>.py`,
   `ninja OpenSCAD`, run, `git stash pop`); re-run the full corpus +
   `FreeCADCmd -t OpenSCADTest.app.test_importCSG`.

## Importer defects found & fixed with this harness (branch `fix-csg`)

All in `src/Mod/OpenSCAD/importCSG.py` unless noted; each has a regression
test in `OpenSCADTest/app/test_importCSG.py`.

1. **`intersection()` with ≠ 2 children crashed** (`AttributeError ...
   'Base'`): the eager `mycommon.Shape = Base.Shape.common(Tool.Shape)` ran
   unconditionally but `.Base/.Tool` exist only in the 2-child branch.
   Moved into that branch, mirroring `fuse()`. (The same eager line was
   removed from `difference` upstream in 2c6af06fe96 for the same reason.)
2. **Null-shape crash chain** (`ValueError: Null input shape` in `fuse`):
   `checkObjShape` received *lists* from single-child groups (guard was a
   silent no-op) and its recompute was single-level, unable to resolve lazy
   `Offset2D → extrusion` dependency chains. Now flattens lists and uses
   `obj.recompute(True)`.
3. **Refine corruption**: Part booleans default to the user's
   `Mod/Part RefineModel` preference (default **true**); `removeSplitter`
   on OpenSCAD's tangent/near-coincident geometry (offset results) produces
   self-intersecting shells that invalidate downstream booleans. All
   importer-created booleans now go through `addBoolean()` → `Refine=False`.
4. **`%` background modifier ignored**: OpenSCAD excludes `%` subtrees from
   the rendered result; the importer fused them in (and its label-prefix
   code dead-coded on a list). `%` subtrees are now removed from the
   document (`p_statementwithmod`).
5. **Orphan circles**: `p_circle_action` created a `circle` object and then
   shadowed it with a second `Draft.makeCircle()` object, leaking the first
   as an extra visible root in 18/31 corpus cases (polluted exports by up
   to 164 mm bbox). The redundant `makeCircle` call is gone.
6. **2D boolean fragmentation** (fillets silently lost): OCC's general fuse
   *tiles* overlapping coplanar faces instead of merging regions, so
   `offset(+r)` offset every tile separately and `offset(-r)` shrank them
   back — the closing fillet vanished while area stayed plausible. New
   `UnifyFaces` FeaturePython proxy (`OpenSCADFeatures.py`; survives
   document recomputes, unlike an eagerly assigned `.Shape`) re-fuses the
   face fragments and `removeSplitter`s them into whole region faces;
   `importCSG` wraps every 2D boolean result and every 2D `offset()` source
   with it (`is2DObjs` / `unifyFaces`).
7. **OCC `BRepOffsetAPI_MakeOffset` SIGSEGV**: crashes on faces whose wires
   are single-edge periodic full circles (exactly what an `offset()` of a
   circular hole produces, so offset-of-offset chains died). Workaround in
   `UnifyFaces.splitFullCircles`: such wires are rebuilt as two arcs via
   `FaceMakerBullseye`.
8. **`offset()` edge cases** (all render EMPTY in OpenSCAD, all crashed or
   relied on parser error recovery in the importer):
   * childless `offset(r=1);` — what OpenSCAD emits for both `offset(r=1);`
     and `offset(r=1) {}` — had no grammar rule (silent parse error);
     explicit empty rule added;
   * an offset whose children were all dropped (e.g. a single `%`
     background child) dereferenced a `None` source; now yields empty;
   * a 3D child hit the half-written `subobj[0].Shape.makeOffset` branch
     (`TypeError`); `offset()` is 2D-only in OpenSCAD ("Ignoring 3D child
     object for 2D operation"), so the importer now warns, removes the
     consumed child subtree, and yields empty. (FreeCAD's `makeOffset`
     *could* round a solid's edges, but that would diverge from OpenSCAD
     ground truth — 3D rounding is `minkowski()` territory.)

Known, deliberately untouched: GUI-mode behavior of `%`-removal and
`UnifyFaces` tree display has only been exercised headless; the
hull()/minkowski() external-openscad path is configured but has no corpus
coverage.

## Status

35 corpus cases: **35/35 convert, 35/35 MATCH** ground truth
(vol err ≤ 0.5 %, bbox Δ ≤ 0.02 mm; truss cases ≤ 0.016 % area error),
0 leaked roots. Unit suite: 39/39 (`FreeCADCmd -t OpenSCADTest.app.test_importCSG`).
