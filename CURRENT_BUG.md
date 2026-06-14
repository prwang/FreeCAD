# CURRENT_BUG — A4: resize() leaks the un-resized source as an orphan root

## Observation
- **Symptom:** `resize(){ ... }` imports as TWO document roots: the correct
  baked `Matrix Deformation` solid AND the original un-resized child solid.
  The summed-STL validation double-counts; when the source has a huge extent the
  leak dominates.
- **File/repro:** `/tmp/resize_min.csg`:
  `resize(newsize=[0,0,0.5]){ cube([6,6,1e10]); }` → 2 roots: `Matrix_Deformation`
  (6×6×0.5, vol = 18.0, valid) + leaked `cube` (vol = 3.6e11).
- **Corpus impact:** `t3d__resize-tests` vol_err = 4.06e9 %,
  `t2d__resize-2d-tests` = 40650 %.
- **Stage:** import succeeds (no crash); geometry/root-count wrong.

## Hypotheses
- **H1 — orphan-source leak in `p_resize_action`.** The rule builds
  `new_part = doc.addObject("Part::FeaturePython",'Matrix Deformation')` with
  `transformGeometry(scale)` but never consumes the source `p[6][0]`; it only
  `p[6][0].ViewObject.hide()`s it, and only under `gui`. Headless leaves the
  source as a live root. Independently testable: count roots after a resize
  import headlessly.
- **H2 — `transformGeometry` produces a wrong/extra shape at extreme scale.**
  The 5e-11 Z scale could be miscomputed → spurious second solid. Testable: check
  the `Matrix Deformation` volume in isolation against the analytic 18.0.
- **H3 — comparator/harness double-counts a single correct root.** Testable: list
  the actual document objects, not just the summed volume.

## Evidence log
- Probe `/tmp/resize_test.csg` (`resize([4,0,0]) cube([2,2,2])`, openscad-generated)
  headless, list ALL document objects + InList:
  - `OBJ cube type=Part::Box vol=8.0 null=False InList=[]`
  - `OBJ Matrix_Deformation type=Part::FeaturePython vol=16.0 null=False InList=[]`
  → **2 objects, both roots** (InList empty). Matrix_Deformation = 4×2×2 = 16 exactly.
- (note) A hand-written `auto=[false,false,false]` csg silently no-ops the resize
  (the rule's `auto[r]=='1'`/`new_size[r]=='0'` string compares expect openscad's
  numeric formatting). Always generate the repro via `openscad -o`.

## Verdict
- **H1 ACCEPTED.** Exactly two roots; the source `cube` (Part::Box, vol 8) is a
  real live document object with no consumer — the orphan leak.
- **H2 REJECTED.** `Matrix_Deformation` is analytically exact (vol 16 = 4×2×2);
  `transformGeometry` is correct.
- **H3 REJECTED.** The leaked root is a genuine `Part::Box` document object, not a
  harness artifact.
- Fix: after baking `new_part.Shape`, remove `p[6][0]` + its `OutListRecursive`
  subtree, mirroring A3#8 (`ac08e5e2c5`). **APPLIED + GREEN** (unit 55/55; repro
  `resize([4,0,0]) cube([2,2,2])` → 1 root vol 16).

## Post-fix associated-corpus check (separate defects surfaced — NOT this bug)
Re-converting/validating the resize corpus after the leak fix:
- `t3d__resize-convexity-tests` → **MATCH** (0.055 %).
- `t3d__resize-tests` 4.06e9 % → **36.9 %** (leak gone; 63 roots, 0 null, 0 invalid).
- `t2d__resize-2d-tests` 40650 % → **14.8 %**.
The blowup (the A4 leak) is eliminated. The residuals are `fc < ref` (missing
volume — opposite sign to a leak) and survive `--refine-fn 128` (NOT faceting).
Isolated against OpenSCAD's own render they are **two distinct, pre-existing
resize defects, separate from the orphan leak**:
- **A6 (clean, tractable):** negative newsize. `resize([-5,0,0]) cube(1)` →
  OpenSCAD **1** (axis with newsize ≤ 0 left unchanged) vs FreeCAD **5** (the
  `new_size[r]=='0'` string-guard misses negatives → factor −5 → mirrored). Clean
  analytic target → Priority-A follow-up.
- **UNKNOWN (postpone, implementation-defined):** `auto=true` on an axis that also
  has an explicit nonzero newsize. `resize([5,0,20],auto=[F,T,T]) cube(9)` →
  OpenSCAD **2000** (= 5×20×20; the auto y-axis follows z's 20/9 factor, not x's)
  vs FreeCAD **125** (the rule `if auto[r]: new_size[r]=new_size[0]` clobbers the
  explicit z=20 with x=5). OpenSCAD's autoscale-factor selection here has no clean
  analytic target → mark UNKNOWN per CLAUDE.md.
These do not block A4: the leak (the dominant error component) is fixed and the
removal dropped nothing (no null/invalid roots). The resize-tests corpus case will
not fully MATCH until A6 + the auto edge are resolved — tracked separately.
