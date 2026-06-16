# BACKLOG — OpenSCAD CSG→STEP importer hardening

In-tree working backlog and planning history for branch `fix-csg`. This is
tracked **dev scaffolding**, NOT the upstream PR docs: it was moved in-tree on
2026-06-16 (from a local plan file) so the planning history is version-controlled
and cross-checkable against the code as it evolves. Per `CLAUDE.md`, the
PR-writing stage will strip/rewrite this into the upstream-facing regression
index; until then we append here as work proceeds. Open work-lists (Categories C
and D, ranked by anticipated difficulty) are at the very end.

---

Branch `fix-csg`, in-container at `/work/FreeCAD`. Build:
`build/headless/bin/FreeCADCmd`. Unit tests:
`FreeCADCmd -t TestOpenSCADApp` (loads from the BUILD tree
`build/headless/Mod/OpenSCAD/` — copy edited sources there to iterate; the
build copies sources at build time so `src/` stays authoritative for commits).

**Global working rules live in `/work/FreeCAD/CLAUDE.md`** (tracked dev-only):
mandatory `CURRENT_BUG.md` (observation/hypotheses/evidence/verdict; no importer
edit until a hypothesis is accepted by conclusive evidence); one minimized
analytic unit test per fixed defect; red→green; both no-regression gates green;
timeout/OOM → Priority C (new-corpus only, not regressions); null-deref bugs are
tractable, prefer fixing.

---

## DONE — compressed facts

**Phases 1–3 (committed earlier).** Headless isolation harness
`src/Mod/OpenSCAD/csg_isolation/` (`csg2step.py` convert+export STL of solid
roots; `run_all.py` one subprocess/file; `validate.py` pure-python volume
[divergence theorem] + bbox vs openscad-rendered reference). 8 importer defects
fixed with red/green unit tests in `OpenSCADTest/app/test_importCSG.py` via the
`utility_create_csg` inline-fixture helper: intersection ≠2 children, null-shape
fuse chain (+`addBoolean` Refine=False, `%` background drop), circle
double-creation, 2D boolean fragmentation (`UnifyFaces` proxy), `MakeOffset`
SIGSEGV (`splitFullCircles`). 35-case dev corpus 35/35 MATCH; harness shipped
in packages. Hold (user): do NOT upstream the SetupQt.cmake headless fixes;
3D `offset()` not the focus.

**Phase 4 (committed `ac4f49aacd`).** Built a 204-case external corpus
(OpenSCAD examples/tests + 9 community repos), discovery kit under
`csg_tests/external/{SOURCES,RESULTS}.md` + `fetch_and_compile.py` (corpus
itself untracked). Harness hardened: `run_all.py` TimeoutExpired bytes/str fix;
4 GB `RLIMIT_AS --mem-gb` cap in all runners (OOM→`stage=oom`/`NO-REF`).
Result: 124 ok / 13 suspect / 67 fail; 78 MATCH / 52 MISMATCH / 7 NO-REF.

**Step 1 — $fn-aware comparator (committed `e97c5e043e`).** Faceting (OpenSCAD
inscribes `$fn` facets; FreeCAD builds the exact smooth solid) is geometry, not
a bug, and below `$fn≈50` it dwarfs a 2 % tolerance. `validate.py` now:
- `--refine-fn N` (authoritative): rewrite every baked `$fn`→N (128 → deficit
  <0.1 %); a mismatch that collapses was faceting, one that survives is real.
  OOM→falls back per-case to envelope (`refine-OOM`).
- analytic envelope (secondary, always on): widen vol tol to `δ/(1−δ)` and bbox
  by `(1−cos(π/n))·extent`; `δ₂=1−sin(2π/n)/(2π/n)` exact, `δ₃≈16.4/n²`
  empirical. **Error basis is `δ/(1−δ)`** (reference is the smaller inscribed
  solid) — the key correction during implementation.

Reclassification: envelope alone 78→**91 MATCH** (13 faceting false-positives
absorbed, incl. the color tests). `--refine-fn 128` over the 39 residual
mismatches: **8 collapse to MATCH** (faceting: example001/004, child-child,
cylinder-diameter, for-tests, linear_extrude-tests, projection-extrude,
rotate-parameters); the rest are real. Full envelope validation backed up at
`csg_external/out/validation.envelope.json`.

**Step 2 — Priority A fixes (7 of 10 committed, each red/green-verified).**
Commit-per-defect on `fix-csg`, newest first:
| commit | defect | OpenSCAD semantic | corpus result |
|---|---|---|---|
| `bc822b9446` | circle fractional `$fn` (crash `int('0.1')`) | round to int | circle-tests **OK** |
| `eb2c64eb66` | resize() zero-extent axis (crash `ZeroDivisionError`) | factor 1.0, axis unscaled | resize-2d/3d **OK** |
| `12cbeaa3b2` | childless rotate_extrude (crash `KeyError 'file'`) | empty | rotate_extrude-tests crash→**SUSPECT** |
| `3d58052896` | intersection null operand (crash `Null input shape`) | A∩∅=∅ (not passthrough) | intersection2-tests **OK** |
| `bf901fb45e` | non-positive square (degenerate plane, vol 107 vs 7) | empty; fuse null-safe (A∪∅=A) | square-tests invalid→**SUSPECT** |
| `c5b73a415d` | multi-path polygon holes dropped | even-odd → outer cut holes | polygon-corner-cases **OK** |
| `205a619b6a` | polygon(points=undef) + silent p_error | empty; warn loudly + continue | parse no longer errors |
| `024eff9443` | null-shape propagation (routing_tiles all-null) | extrude(∅)=∅, A∪∅=A | routing_tiles crash→**OK + MATCH 0.002%** |
| `61d6b153f3` | `inf`/`nan` literals derail parser (drop statement) | inf/nan=undef; undef dim/vertex→empty, undef $fn→default | primitive-inf-tests empty→**2 finite solids (π, 4π/3)**; square-tests no syntax error |

**9 defects committed, each red/green-verified with a minimized analytic test.**
- 8th (`024eff9443`, null propagation): A2#5's degenerate-square null operand
  flowed through two non-null-safe consumers — `linear_extrude` and the
  `>2`-child `Part::MultiFuse`. `fuse()` now filters & consumes nulls up front;
  `linear_extrude` of a null profile → empty. Test
  `test_import_union_drops_empty_operand`.
- 9th (`61d6b153f3`, inf/nan): OpenSCAD emits inf/nan as bare tokens and treats
  them as undef. The lexer tokenised them as identifiers → spurious syntax error
  → PLY recovery dropped the whole statement (so a finite primitive whose only
  oddity was $fn=inf vanished, and primitive-inf-tests imported as nothing).
  Fix: lexer lexes inf/nan as NUMBER; primitives guard non-finite $fn (→ smooth)
  and non-finite dimension/vertex (→ empty) via `all_points_finite`. Test
  `test_import_non_finite_dimension` (cylinder $fn=inf → V=18π; sphere(r=inf) →
  empty; polyhedron inf-vertex → empty).

Gates GREEN: unit suite **51/51**; dev corpus **35/35 conversion + 34 MATCH / 0
MISMATCH / 1 NO-REF** (baseline_preview = OpenSCAD reference-side 120 s timeout,
pre-existing, not a regression).

---

## Answers to the open questions (2026-06-14)

**Is all of group A crash-fixed? — No; the targeted simple-construct crashes
are, a few complex/out-of-scope files degrade instead of crashing, one remains.**
Verified by re-running the crash-class corpus files through the patched importer:
- Cleanly fixed → OK: circle-tests, resize-2d, resize-3d, intersection2-tests,
  polygon-corner-cases, **routing_tiles** (was the null bug → now OK + MATCH).
- → **Priority C** (genuine timeout/heavy compute, new corpus, not regressions):
  jbarr **nodes_graph** (6 K lines, 458 offset), jbarr **rhombitrihexagon**
  (148 K lines, 28855 polygon/offset). The Null-input crash is gone; they now
  just don't finish in 120 s.
- Crash eliminated but degrades (not yet clean): rotate_extrude-tests→SUSPECT.
- `inf`/`nan` primitive family (`61d6b153f3`): square-tests/circle-tests/
  primitive-inf-tests now import cleanly — inf→empty (or $fn=inf→smooth) matching
  OpenSCAD's undef semantics; no more spurious syntax errors. SUSPECT on
  square-tests was the comparator flagging *intended* empty squares, not a bug.
- Still FAIL@parse, NOT addressed:
  - **offset-tests** "RuntimeError: shape is invalid" — a different offset()
    variant, never in A1–A4 scope. → postpone.
  - **rotate_extrude-angle** `file = "45"` — the no-dot guard stops the unpack
    crash, but `process_import_file` then raises "Unsupported file extension".
    This is a malformed/companion-file import (Priority B environmental), not a
    simple-construct crash. → postpone/Priority B.

**The geometry (non-crash) bugs vs anticipated cause:**
- polygon holes (`c5b73a415d`): **matched exactly** — the code's own comment
  "This only pushes last polygon" was the cause (per-path face + `p[0]=` inside
  the loop). Fixed: one face, largest wire outer, others cut as holes.
- non-positive square (`bf901fb45e`): **matched** — degenerate `Part::Plane`.
  Fixed via null-shape operand (kept, not dropped, so booleans stay correct).
- polygon(undef) (`205a619b6a`): grammar-gap cause matched, but the anticipated
  **consequence was wrong** — PLY error recovery already preserves sibling
  geometry, so there was no "whole-library wipeout": the roundany files are
  legitimately empty (degenerate all-undef library compilations; openscad
  renders them empty too). Real fix = stop the spurious syntax error + warn
  loudly.

---

## A2#6 / A3#9 / A3#8 — RESOLVED (2026-06-14, each red/green + repro)

All three previously-postponed items had clean, tractable defects once probed
under the CURRENT_BUG.md discipline (the stale "7e6 % / 50 % / 38 %" figures
were faceting absorbed by the comparator and orphan-root leaks, not
geometry-builder bugs):

| commit | defect | analytic | repro |
|---|---|---|---|
| `ff880cd47a` | A2#6 linear_extrude scale-taper: zero scale component → pipe-shell `gp_Dir` zero-norm → null. Twist now connects base→scaled-top perimeter vertices. | cone=base·h/3 (333.33), wedge=base·h/2 (500), frustum unchanged (583.33) | `bug_repros/20` |
| `3ba221ab68` | A3#9 projection(cut=false) leaked `xy_plane_used_for_projection` orphan root. Plane built inside cut=true branch only. | cut=true cube slice=100; cut=false → no plane root | `bug_repros/21` |
| `ac08e5e2c5` | A3#8 (via polyhedron-nonplanar-tests): non-rigid multmatrix transformGeometry path left the untransformed source as an orphan root (raw 206803 + scaled 1.654). Now removes `part`+subtree. Polyhedron builder itself was already correct. | multmatrix(scale 2) cube(10)=8000, one root; nonplanar-tests 206806→2.9431 (==OpenSCAD 2.94311) | `bug_repros/22` |

Gates after all three: unit **54/54 OK**; dev corpus **35/35 conversion + 35
MATCH / 0 MISMATCH / 0 NO-REF**. CURRENT_BUG.md cleared (`e120905e12`).

---

## A4 / A5 — RESOLVED (2026-06-14, each red/green + repro + corpus A/B)

Both committed, each with a minimized analytic unit test (red→green) and a
`.scad` repro. Gates after both: unit **56/56**; dev corpus **35/35 convert +
35 MATCH**.
| commit | defect | analytic | repro |
|---|---|---|---|
| `b8a90c6d93` | A4 resize() orphan-source leak — only `.hide()`d the source under `gui`; headless left the un-resized child as a stray root → double-count. Now removes `p[6][0]`+subtree after baking. | resize([4,0,0]) cube([2,2,2]) → 1 root vol 16 | `bug_repros/23` |
| `8e36697899` | A5 linear_extrude twist + point-collapse (scale=[0,0]) → null. A2#6 taper branch was gated on Angle==0 → twisted point fell to MakePipeShell → gp_Dir zero-norm. Point apex is twist-invariant → straight pyramid; `_taper_solid` now fires for any both-zero collapse. | twist180/[0,0]→4 (base·h/3), twist90/[0,1]→6 (base·h/2) | `bug_repros/24` |

**Corpus A/B (refs cached): strict improvement, NO regression, but not full MATCH
— each multi-statement OpenSCAD test file bundles SEPARATE pre-existing defects:**
- A4: `t3d__resize-convexity-tests` → MATCH; `t3d__resize-tests` 4.06e9 %→**36.9 %**
  (63 roots, 0 null/invalid); `t2d__resize-2d-tests` 40650 %→**14.8 %**. Residual
  = **A6 + UNKNOWN** below (`fc < ref`, survives `--refine-fn 128` → not faceting).
- A5: `t3d__linear_extrude-scale-zero-tests` 44.8 %→**32.4 %**; `ex__linear_extrude`
  SUSPECT 24.2 %→**OK 3.3 %**; `linear_extrude-tests` MATCH (unchanged);
  `invisible-tests` unchanged 34.7 %. Residual = **twist + nonzero-scale**
  MakePipeShell shells that come out invalid and fall back to a Compound (a
  pre-existing cluster the A5 point-fix does not touch).

### A6 — resize() negative newsize (clean, tractable; surfaced while validating A4)
- **Observation (vs OpenSCAD render):** `resize([-5,0,0]) cube(1)` → OpenSCAD **1**
  (an axis with newsize ≤ 0 is left unchanged) vs FreeCAD **5** (the
  `new_size[r]=='0'` string-guard in `p_resize_action` only catches an exact 0, so
  a negative passes through → factor −5 → mirrored cube).
- **Fix plan:** treat `float(new_size[r]) <= 0` (after the auto pass) the same as
  the zero case → leave that axis unchanged (factor 1.0). Clean analytic target.
- **Minimized test:** `resize([-5,0,0]) cube([1,1,1])` → 1 root, vol **1**.
  `bug_repros/25`. (Won't by itself flip resize-tests to MATCH — the UNKNOWN
  auto-interaction below dominates that file.)

### UNKNOWN (postpone) — resize() auto=true on an axis with an explicit newsize
- `resize([5,0,20],auto=[false,true,true]) cube(9)` → OpenSCAD **2000** (the auto
  y-axis follows z's 20/9 factor, not x's 5/9; 2000 = 5×20×20) vs FreeCAD **125**
  (the rule `if auto[r]: new_size[r]=new_size[0]` clobbers the explicit z=20 with
  x=5). OpenSCAD's autoscale-factor selection when an axis is both auto AND has an
  explicit nonzero newsize has no clean analytic target → mark UNKNOWN per
  CLAUDE.md. This (not A4/A6) is the dominant residual in `t3d__resize-tests`.
  [SUPERSEDED by A7 below — turned out to be a concrete rule, now MATCHes.]

### (historical note)
What the sweep first flagged as a "multmatrix 1e10 blowup" was, on probing, the
A4 resize() orphan leak — the 1e10 is in the cube *source*, kept as
`resize(){cube(...)}` in the .csg (NOT baked to multmatrix).

### A4 — resize() leaks the un-resized source as an orphan root
- **Observation (repro `/tmp/resize_min.csg`):**
  `resize(newsize=[0,0,0.5]){ cube([6,6,1e10]); }` imports as **2 roots** —
  the correct `Matrix_Deformation` (6×6×0.5, **vol = 18.0, valid**) AND the
  leaked source `cube` (**vol = 3.6e11**). Summed-STL volume double-counts and,
  with the 1e10 extent, the leak dominates → corpus `t3d__resize-tests`
  vol_err = 4.06e9 %, `t2d__resize-2d-tests` = 40650 %.
- **Root cause (ACCEPTED by repro):** `importCSG.p_resize_action`
  (`importCSG.py` ~L510–550) builds `new_part = doc.addObject(... 'Matrix
  Deformation')` with `transformGeometry(scale)` but **never consumes the source
  `p[6][0]`** — it only `p[6][0].ViewObject.hide()`s it, and *only when `gui`*.
  Headless leaves the source as a live document root. `transformGeometry` itself
  is correct even at the 5e-11 scale (result = 18 exactly), so this is purely the
  orphan leak — **the identical class A3#8 fixed for `p_multmatrix_action` path 4,
  which did not touch resize's separate transform block.**
- **Fix plan:** after `new_part.Shape = ...transformGeometry(...)`, remove the
  source subtree exactly as A3#8 did:
  `for obj in p[6][0].OutListRecursive + [p[6][0]]: doc.removeObject(obj.Name)`
  (guarded try/except; keep the GUI `.hide()` path intact for the
  useViewProviderTree case, or remove unconditionally since the shape is fully
  copied into `new_part`). Mirror `ac08e5e2c5`.
- **Minimized test (red→green, `utility_create_csg`):**
  `resize(newsize=[4,0,0]){ cube([2,2,2]); }` → **exactly ONE solid root**,
  volume **16** (4×2×2; the `0` axes stay 2 per OpenSCAD "0 = leave unchanged").
  Assert `len(roots)==1` (the red state has 2: leaked 8-unit cube + 16-unit
  result) AND `vol==16`. `.scad` repro `bug_repros/23_resize_source_leak.scad`.

### A5 — linear_extrude twist + zero-scale-component → null shape
- **Observation (repro `/tmp/twist_min.csg`):**
  `linear_extrude(height=3, twist=180, slices=20, scale=[0,0]){ square([2,2]); }`
  → `stage=invalid-shape`, root `transform_extrude` **isNull=True** ("all root
  shapes are null"). Drives corpus `t3d__linear_extrude-scale-zero-tests`
  (44.8 %) and contributes to `linear_extrude_invisible-tests` (34.7 %),
  `ex__linear_extrude` (24 %).
- **Root cause (ACCEPTED by repro):** `OpenSCADFeatures.Twist.execute`
  (`OpenSCADFeatures.py` L459) — the A2#6 degenerate-taper branch is gated on
  `fp.Angle.Value == 0.0`. With `twist != 0` AND a zero scale component the code
  falls through to the `MakePipeShell` between the base wire and the zero-area
  scaled top wire → `gp_Dir() zero norm` → null. A2#6 deliberately covered only
  the no-twist case; this is its twist-bearing sibling.
- **Fix plan:** extend the degenerate-taper handling to `twist != 0`. The current
  `_taper_solid` rules straight lines base-perimeter→scaled-top; with twist the
  side is a helical ruled surface, so build the solid by **lofting/sewing through
  the `slices` intermediate cross-sections** — wire `k` = base wire scaled by the
  per-height taper factor and rotated by `twist·(k/slices)` — capping the
  degenerate final slice with a triangle fan to the apex (scale=[0,0] → point) or
  edge (scale=[0,1] → line). Slice count = `slices`, so the comparator's
  $fn/slices envelope covers the discretization. Reuse `_planar_faces`; orient by
  Volume sign as A2#6 does.
- **Analytic target (twist preserves cross-sectional area, so volumes equal the
  A2#6 no-twist values):** `twist=180, scale=[0,0]` square([2,2]) h=3 →
  cone-like taper-to-point **vol = base·h/3 = 4·3/3 = 4**; `twist=90, scale=[0,1]`
  → taper-to-line **vol = base·h/2 = 4·3/2 = 6**.
- **Minimized test (red→green):** the two cases above; red state = null shape
  (import fails "all root shapes are null"). `.scad` repro
  `bug_repros/24_linear_extrude_twist_scale_zero.scad`.

### Sweep clusters intentionally NOT promoted (evidence-based)
- **color()/group overlap** (5 MISMATCH; `fc>ref` in all) — overlapping separate
  colored solids double-counted in the summed STL vs OpenSCAD's unioned render;
  FreeCAD's document (per-part color preserved) is arguably more faithful.
  Validation-methodology artifact, not a geometry bug.
- **Faceting residue** (~12 MISMATCH at 2–6 %, curved prims) — collapses under
  `validate.py --refine-fn 128`; geometry, not a defect.
- **minkowski / hull / offset → null** (9 conversion fails + gridfinity 339 %,
  heart_purse 68 %) — biggest *geometry* cluster but algorithmically hard in OCC
  (no cheap convex-hull / Minkowski-sum); stays postponed.
- **text() → legacy `dxfReader=None`** (26) and **companion-file imports** (~5) —
  environmental Priority B; the modern C++ `Import.readDXF` path could unblock the
  text cases but reworking `OpenSCAD2Dgeom.importDXFface` is out of the
  CSG-geometry focus and previously parked.

## STILL POSTPONED (genuinely complex / ill-defined target)

- **True shadow projection** `projection(cut=false)` geometry — silhouette has
  no clean OCC/analytic target; intentional placeholder (A3#9 fixed only the
  plane leak, not the unsupported silhouette).
- **Non-planar polyhedron faces via `makeFilledFace`** — for the corpus cases
  the result already matches OpenSCAD (near-cube 1.0==1.0, giant scaled
  1.654==1.654); OpenSCAD's own triangulation of non-planar faces is
  implementation-defined, so no further analytic target.
- **Priority B (environmental, not importer geometry):** text()→legacy
  `dxfReader` missing ×26; companion files not harvested ×6; rotate_extrude
  `file="45"` import.

---

## REMAINING STEPS (immediate next first)

DONE: 9 Priority-A defects + A2#6/A3#9/A3#8 + **A4 (`b8a90c6d93`) + A5
(`8e36697899`)** committed; full 204-case sweep run (0 regressions, 91→103 MATCH,
archived). A4/A5 each red/green + repro + corpus A/B (strict improvement, no
regression). Validating A4/A5 surfaced new, narrower defects (A6 + UNKNOWN +
twist-invalid-shell, see A4/A5 section). Next:

1. ~~**A6 — resize() negative newsize**~~ DONE `561edf6ebe`: numeric
   `float(new_size[r]) <= 0` guard → axis unchanged. `resize([-5,0,0]) cube(1)`
   red vol 5 → green vol 1; `bug_repros/25`; unit 57/57; dev 35/35 MATCH.
2. ~~**Full 204-case regression sweep (A4+A5+A6)**~~ DONE: **0 regressions**
   (0 conversion, 0 validation) vs the postfix-sweep baseline `e120905e12`.
   Net +1 conversion ok (134→135, `ex__linear_extrude` suspect→ok) and +1 MATCH
   (103→104, `t3d__colored-nodes`); big below-tolerance drops on resize-tests
   (4e9 %→36.9 %), resize-2d (40650 %→14.8 %), linear_extrude-scale-zero
   (44.8 %→32.4 %). Archived
   `results_archive/20260614T154309Z__postfix-A4A5A6-sweep__837c483c40/`.
3. **Step 3 — finalize PR shape (deferred):** regression index + RESULTS.md
   reclassification once the importer work settles.

UPDATE (2026-06-14, later): pinned both residuals to OpenSCAD 2021.01 and
converged what is convergeable:
- **A7 `07d36bceee` — resize auto-scale.** The former "UNKNOWN" was a concrete,
  deterministic OpenSCAD rule (auto axis with newsize 0 → MAX explicit per-axis
  factor), reverse-engineered from a render battery and matched exactly. The
  WHOLE resize cluster now MATCHes (resize-tests 36.9 %→0.24 %, resize-2d
  14.8 %→0.0 %, convexity MATCH). A6 `561edf6ebe` (negative newsize → unchanged)
  folded in.
- **A8 `e3b64af870` — twist + line collapse.** Single-wire twisted taper-to-line
  (e.g. twist180 scale=[0,1]) no longer null — lofts a valid solid. A holed
  twisted taper-to-line genuinely self-intersects (no clean OCC solid) → left
  empty, the true UNKNOWN. scale-zero-tests 32.4 %→21 %.
- **Pure twist is NOT a bug:** FreeCAD's smooth helical sweep is the EXACT
  slices→∞ limit; OpenSCAD's default-slices render converges to it
  (2050/2020/2005/2001 → 2000). validate.py `--refine-fn` now refines `slices`
  too (`6675ba2ecc`) so this classifies as faceting.

Full sweep after A7/A8: **103→106 MATCH across the session, 0 regressions**
(archived `...__postfix-A7A8-resize-converged__1fec9ada23`).

Still postponed (genuinely hard / separate, none Priority A): holed twisted
taper-to-line (self-intersecting); ex__linear_extrude bbox offset (non-faceting);
linear_extrude_invisible-tests (34.7 %); minkowski/hull null cluster; text→
dxfReader Priority B.

POSTPONE/UNKNOWN (documented above, not Priority A): linear_extrude twist +
nonzero-scale invalid MakePipeShell shell (general sweep-robustness, not a clean
degenerate-collapse case).

---

## Headless end-user entry point + xfail messages (2026-06-16)

Made the conversion path usable by a normal headless user (no GUI), and made
its failures legible. Tracked harness changes only (no importer geometry edit):

- **`csg_isolation/csg2step.sh`** (new, executable) — the user-facing wrapper.
  FreeCADCmd is a custom interpreter that opens positional args as *documents*
  (verified: `FreeCADCmd script.py foo.csg` re-imports foo.csg AND tries to read
  it as STEP); a leading `--` suppresses that but is fragile, so the wrapper
  keeps the env-var channel (`CSG2STEP_IN/OUT`) and just locates FreeCADCmd
  ($FREECADCMD → `<prefix>/bin` → PATH, same logic as run_all.py). Maps the
  driver's status → exit code: 0 ok/suspect, 2 unsupported (xfail), 1 error,
  64 usage. Surfaces only the friendly block (filters FreeCADCmd's banner).
- **`csg2step.py`** — added `friendly_message()` + `_classify()` mapping the two
  environmental xfail signatures to plain text (readDXF → "uses text()/DXF,
  needs Draft module"; missing file → "imports an external file '<name>' not
  found"), a `CSG2STEP_HUMAN` human-output mode (friendly summary instead of the
  JSON marker), and **skips the validation-only STL sidecar in human mode**.
  Additive only: the JSON marker contract run_all.py parses is unchanged (now
  carries an extra `category` field). The STL skip also removes the lone hard
  crash from the user path — `ex__example020`'s segfault is in the OCC threaded
  STL mesher, *after* the STEP is written, so STEP-only now converts it cleanly
  (3 solids, 1.27 MB STEP, exit 0). Verified: OK/text-xfail/missing-file-xfail/
  real-fail/usage all correct; run_all.py 4/4 unchanged.

### Corpus error triage (latest sweep `1fec9ada23`, 204 cases)
135 OK · 18 suspect · 51 non-OK. Of the non-OK: **3 resource-limit** (Priority C:
`keyv2__sa_ergo` oom, `jbarr__rhombitrihexagon` + `t3d__minkowski3-difference-test`
timeout), **32 xfail** now given friendly messages (26 text/DXF readDXF, 6
missing external asset), **1 STL-mesher crash** (`ex__example020`, now fixed on
the user path), leaving the two work-lists below.

### Category C — real defects, NO output produced (15) — ascending difficulty
Genuine importer/geometry bugs; each needs a CURRENT_BUG.md + minimized repro
per CLAUDE.md. Easiest/highest-value first:
1. `t3d__rotate_extrude-angle` — `ValueError: Unsupported file extension`. Smells
   like an importer-internal path bug (`file="45"` → extension-less temp), not
   deep geometry. Likely the cheapest, clean target. *(easy)*
2. `t2d__offset-tests` — `RuntimeError: shape is invalid`. A different offset()
   variant than the ones already handled; offset is partly supported. *(easy-mid)*
3. `roundany__shell2d` — empty-result; 2D shell, almost certainly offset-related. *(mid)*
4. `roundany__polyround` — empty-result; rounding library (offset/fillet). *(mid)*
5. `ex__module_recursion` — `CADKernelError: Unorientable shape` in a FUS over a
   recursive-module union; boolean-orientation robustness. *(mid)*
6. `dactyl__dactyl-top-right` — `Self-intersecting wire` in FUS, real keyboard
   model; geometry-robustness on messy input. *(mid-hard)*
7–13. **minkowski/hull null cluster** (no native OCC convex-hull / Minkowski-sum;
   algorithmically hard, several likely UNKNOWN): `t2d__minkowski2-tests`
   ("Cannot transform null shape"), `t2d__minkowski2-crack`,
   `t2d__minkowski2-hole-tests`, `t3d__minkowski3-erosion`,
   `t3d__nullspace-minkowski`, `t2d__hull2-tests`, `t2d__control-hull-dimension`.
   *(hard)*
14. `keyv2__plate_generation` — all-null in a real model (minkowski/hull inside). *(hard)*
15. `threads__threads` — all-null; thread library, sweep/minkowski-heavy. *(hard)*

### Category D — SUSPECT: STEP written but ≥1 invalid sub-shape (18) — ascending difficulty
These already export; the fix is making the flagged sub-shape valid (lower stakes
than C — the user gets a file, just geometrically suspect). Easiest first:
1. `t2d__square-tests` (square001/004/005/006) — degenerate/zero squares; extends
   the existing non-positive-square guard. *(easy)*
2. `t2d__nullspace-2d` (square) — degenerate square in an empty-space test; same. *(easy)*
3. `t2d__circle-tests` (circle001) — single degenerate circle; analytic. *(easy)*
4. `t3d__sphere-tests` (sphere001) — single sphere validity; analytic. *(easy)*
5. `t2d__polygon-tests` (polygon009) — one self-touching/degenerate polygon. *(easy-mid)*
6. `t2d__scale2D-tests` / 7. `t3d__scale3D-tests` / 8. `t3d__linear_extrude-tests`
   (LinearExtrude) — extrude of an invalid 2D base; likely shared root cause with
   the 2D primitives above. *(mid)*
9. `t2d__difference-2d-tests` / 10. `t3d__difference-tests` (difference) — boolean
   yielding an invalid solid. *(mid)*
11. `t3d__rotate_extrude-tests` (RotateExtrude) — revolve producing invalid. *(mid)*
12. `t3d__linear_extrude-scale-zero-tests` (Group) — ties to A5/A8 twist work; the
    holed-twisted-taper UNKNOWN lives here. *(mid-hard)*
13. `jbarr__heart_purse` / 14. `jbarr__nodes_graph` (Offset2D) — offset on real
    models. *(hard)*
15. `t2d__projection-cut-tests` / 16. `t3d__colored-nodes` (minkowski) — *(hard)*
17. `t3d__hull3-tests` (hull) — *(hard)*
18. `gridfin__gridfinity-spiral-vase` (difference012) — complex real-world model. *(hard)*

---

## Category C — easiest 5 RESOLVED (2026-06-16)

Worked the 5 easiest Category-C cases under the CURRENT_BUG.md discipline. Goal:
xfail-with-reason OR real output (→ Category D), no regression. Gates after the
batch: unit suite **64/64 OK**; dev corpus **35/35 convert + (validate) MATCH**.

| # | case | was | now | commit |
|---|---|---|---|---|
| C1 | `t3d__rotate_extrude-angle` | FAIL@parse `ValueError: Unsupported file extension` | exports, 73 obj (suspect) → **Cat D** | `65223cb91b` |
| C2 | `t2d__offset-tests` | FAIL@parse `RuntimeError: shape is invalid` | exports, 97 obj (suspect) → **Cat D** | `39eebb0263` |
| C3 | `roundany__shell2d` | FAIL@empty-result (hard error) | friendly **EMPTY** (exit 3) | `42bd59a2f5` |
| C4 | `roundany__polyround` | FAIL@empty-result (hard error) | friendly **EMPTY** (exit 3) | `42bd59a2f5` |
| C5 | `ex__module_recursion` | FAIL@parse `CADKernelError: Unorientable shape` (crash) | crash fixed → **Priority-C timeout** (heavy 2047-boolean model) | `1af659d485` |

- **C1** `p_rotate_extrude_file`: the deprecated `file=` (2D-profile import) form
  with an unopenable file now renders empty + warns (mirrors import-of-missing
  and the childless path), instead of aborting the whole document. Repro 29.
- **C2** `p_offset_action`: a null/degenerate operand (`square([0,0])`) is now
  guarded before `.Volume` → offset-of-empty renders empty (consumed), instead
  of `RuntimeError: shape is invalid` aborting. Repro 28.
- **C3/C4**: NOT importer bugs — both models genuinely evaluate to empty (empty
  extrude body; `polygon(undef)`), exactly as OpenSCAD renders them. The fix is
  in the driver: a clean run with no shaped roots is classified `empty` (its own
  friendly category, exit 3), not a hard error. Importer regression guards
  assert the correct empty output. No `.scad` repro (no importer defect).
- **C5** `fuse` single-fuse path: one node's tool operand was an invalid
  multi-wire 2D face (accumulated from a long chain of overlapping-rectangle
  unions; OCC "Unorientable"). New `repair2DFaces` (ShapeFix on a mutable copy,
  holes-preserving; outer-wire fallback) + a try/except that repairs operands
  and retries, baking the result into a static `Part::Feature`. The crash is
  gone; `ex__module_recursion` is also genuinely heavy (2× recompute over 2047
  nested booleans → > 540 s), so it now lands as an honest **Priority-C timeout**
  rather than a crash. Unit test `test_repair_invalid_2d_face_for_fuse`
  (deterministic synthetic invalid hole-face; the emergent canopy face has no
  minimal `.scad` form). Repro 30.
