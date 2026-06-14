# CURRENT_BUG — A5: linear_extrude twist + zero-scale-component → null shape

## Observation
- **Symptom:** `linear_extrude(twist≠0, scale=[0,*])` (a zero scale component)
  imports as a NULL shape → `stage=invalid-shape` / "all root shapes are null".
- **Repro:** `/tmp/tw/point.csg` (`twist=180, scale=[0,0] square([2,2]) h=3`) and
  `/tmp/tw/line.csg` (`twist=90, scale=[0,1]`).
- **Corpus impact:** `t3d__linear_extrude-scale-zero-tests` (44.8 %),
  `linear_extrude_invisible-tests` (34.7 %), `ex__linear_extrude` (24 %).
- **OpenSCAD reference render:** point = 4.087, line = 6.048 (the discretized
  20-slice overshoot above the smooth limits base·h/3 = 4 and base·h/2 = 6;
  twist preserves cross-sectional area so the volume is scale-driven only).

## Hypotheses
- **H1 — the A2#6 degenerate-taper branch is gated on `Angle==0`.**
  `OpenSCADFeatures.Twist.execute` L459: `if fp.Angle.Value == 0.0 and (abs(sx) <
  1e-9 or abs(sy) < 1e-9) ...`. With twist≠0 the code skips `_taper_solid` and
  falls through to `MakePipeShell` between the base wire and the zero-area scaled
  top wire → `gp_Dir() zero norm` → null. Testable: import the repro and confirm
  the root shape is null on twist≠0 but valid on the same case with twist=0.
- **H2 — the profile/scale parse is wrong** (e.g. scale not reaching Twist).
  Testable: print fp.Scale / fp.Angle inside execute.

## Evidence log
- Import probe on COMMITTED OpenSCADFeatures (build tree):
  - `point` twist=180 scale=[0,0]  → `transform_extrude null=True`  ← NULL bug
  - `line`  twist=90  scale=[0,1]  → `transform_extrude null=False vol=6.0`  (works!)
  - `point_notwist` twist=0 scale=[0,0] → `null=False vol=4.0`  (A2#6 path)
- So the null is NARROWER than assumed: only the **both-components-zero** (top
  collapses to a POINT) case under twist≠0. The one-zero (line) case already
  builds via MakePipeShell — its top wire is a degenerate-but-nonzero segment, so
  no zero-norm — and gives exactly 6.0 (= base·h/2, even cleaner than OpenSCAD's
  20-slice 6.048).

## Verdict
- **H1 ACCEPTED, refined.** The `Angle==0` gate skips `_taper_solid` for the
  point-collapse-with-twist case, dropping it to MakePipeShell where the
  zero-area point top → `gp_Dir` zero norm → null. Confirmed: same scale builds
  fine at twist=0; the line variant is unaffected (MakePipeShell handles it).
- **H2 REJECTED.** fp.Scale/fp.Angle reach execute correctly (line builds vol 6;
  no-twist point builds vol 4).
- **Key geometry fact:** a point apex sits ON the twist axis, so twisting leaves
  it invariant — the correct solid is exactly the straight pyramid (base·h/3 = 4),
  which `_taper_solid` already produces. Fix: fire `_taper_solid` whenever the top
  collapses to a point (`abs(sx)<eps and abs(sy)<eps`), regardless of Angle; keep
  the existing no-twist one-zero (line) branch; leave the twist+line case on its
  working MakePipeShell path. (Difference vs OpenSCAD's 4.087 is 2.1 % discretized
  overshoot — faceting-class, absorbed by the validate.py envelope.)

## Post-fix associated-corpus check (improvement, no regression)
A/B vs committed (pre-A5) OpenSCADFeatures on the linear_extrude cases:
- `t3d__linear_extrude-scale-zero-tests`: 44.8 % → **32.4 %** (bbox_d 5.86 → 3.0).
- `ex__linear_extrude`: SUSPECT 24.2 % → **OK 3.3 %** (cleared the invalid
  `transform_extrude002`; bbox_d 28.2 → 4.37).
- `t3d__linear_extrude-tests`: MATCH 0.9 % before and after (unchanged).
- `t3d__linear_extrude-parameter-tests`: MATCH; `linear_extrude_invisible-tests`
  unchanged 34.7 % (a variant my branch does not touch).
The pre-existing SUSPECT (invalid shapes) on scale-zero-tests / linear_extrude-tests
is present at HEAD before A5 — NOT introduced by this fix (A5 only adds the
point-collapse branch; it removed an invalid shape, never added one). The residual
MISMATCH is a separate pre-existing cluster (twist + nonzero-scale shells that the
MakePipeShell path leaves invalid and falls back to a Compound), tracked separately.
Unit 56/56; dev corpus 35/35 convert + 35 MATCH.
