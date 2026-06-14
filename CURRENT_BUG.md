# CURRENT BUG — (none active)

No bug under investigation. Last resolved (this session, in order):
- A2#6 `linear_extrude` scale-taper (zero scale component) → committed
  `ff880cd47a`. Twist.execute builds the tapered solid by connecting base
  perimeter vertices to scaled-top vertices when a scale component is 0
  (pipe-shell's sweep direction was undefined). cone=base·h/3, wedge=base·h/2.
- A3#9 `projection(cut=false)` plane leak → committed `3ba221ab68`. The
  `xy_plane_used_for_projection` helper is now built inside the cut=true branch
  only, so cut=false no longer leaves a stray plane root. True shadow
  projection remains an honest placeholder (no clean OCC/analytic target).
- A3#8 polyhedron / non-rigid multmatrix leak → committed `ac08e5e2c5`. The
  polyhedron builder was already correct; the defect was p_multmatrix_action's
  transformGeometry fallback leaving the untransformed source as an orphan
  root. Now it removes `part` + subtree after baking. nonplanar-tests
  206806→2.9431 (== OpenSCAD 2.94311).

Gates after all three: unit 54/54 OK; dev corpus 35/35 conversion + 35 MATCH /
0 MISMATCH / 0 NO-REF.

When the next non-trivial bug appears, overwrite this file with the mandatory
template (per CLAUDE.md — do NOT edit importer code before a hypothesis is
accepted by conclusive evidence that also rejects the competitors):

## Observation
- exact symptom, file, reproduction, stage/error.

## Hypotheses (each independently testable)
- H1: …
- H2: …

## Evidence log
- probe → what it showed.

## Verdict
- which hypotheses ACCEPTED/REJECTED and why.
