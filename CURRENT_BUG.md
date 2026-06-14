# CURRENT_BUG — A8: linear_extrude twist + line-collapse (one zero scale) → null

## Observation
- `linear_extrude(twist=180, slices=20, scale=[0,1]) square([2,2])` (h=3) imports
  as a NULL shape. Asymmetric: `scale=[1,0]` (twist 180) and `scale=[0,1]` (twist
  90) both build fine (valid, vol 6.0). The dominant remaining contributor to
  `t3d__linear_extrude-scale-zero-tests` (two null `Group` roots).
- A5 fixed only the both-zero (point) collapse with twist; the one-zero (line)
  collapse with twist stays on the MakePipeShell path, which fails for this combo.

## Evidence (FreeCAD vs OpenSCAD 2021.01 render)
| twist | scale | FreeCAD | OpenSCAD |
|---|---|---|---|
| 180 | [0,1] | **NULL** | 6.106 |
| 180 | [1,0] | valid 6.0 | 6.156 |
| 180 | [0,0] | valid 4.0 (A5) | 4.087 |
| 90  | [0,1] | valid 6.0 | 6.106 |
- The null originates in the MakePipeShell block: `assert(pipe_shell.isReady())`
  / `pipe_shell.build()` raises for the [0,1]+twist180 sweep, aborting the face
  loop before `fp.Shape` is set.

## Verdict
- **ACCEPTED:** MakePipeShell's helical sweep between the base wire and the
  rotated zero-area top segment is ill-conditioned for some twisted line
  collapses and raises, leaving the result null. The smooth sweep is the right
  geometry where it succeeds (it gives the exact base·h/2), so keep it — but make
  it resilient: wrap the sweep, and for a single-wire one-zero (line) twisted
  profile fall back to building the solid by lofting through the rotated+scaled
  cross-sections (`_twisted_taper_solid`). Twist preserves area, so the volume
  still converges to base·h/2.
- Non-degenerate failures keep the existing Compound-of-faces fallback (no
  geometry silently dropped).

## (separate, NOT this bug) pure-twist faceting is a comparator gap
For twist + nonzero scale, FreeCAD's smooth helical sweep is the EXACT solid
(twist90 square h=20 = base·h = 2000); OpenSCAD's default-`slices` render
overshoots (2117) and converges to 2000 only as slices→∞ (2050/2020/2005/2001 at
slices 20/50/200/1000). This is `slices`-driven faceting, which `validate.py
--refine-fn` does not currently rewrite. Fix is in the comparator (refine
`slices` like `$fn`), not the importer — handled separately.
