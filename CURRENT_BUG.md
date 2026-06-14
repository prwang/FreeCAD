# CURRENT BUG — A2#6 linear_extrude scale-taper (scale with a zero component)

## Observation
- File family: ex__linear_extrude / linear_extrude-tests (scale-zero 73 %).
- Repro: `linear_extrude(height=10, scale=0) square([10,10]);` (OpenSCAD bakes
  `scale=0` → `scale=[0,0]`) and `linear_extrude(height=10, scale=[0,1])
  square([10,10]);`.
- Symptom: imported `transform_extrude` root has **null shape, vol 0** for any
  scale component == 0. Non-degenerate scale (frustum `[0.5,0.5]`) is fine
  (vol 583.333 exact).
- Stage: `OpenSCADFeatures.Twist.execute` — recompute leaves `fp.Shape` null;
  no Python-level crash in the importer.

## Hypotheses (each independently testable)
- H1: scaling a face by a 0 component makes a zero-area `upper_face`; the
  `MakePipeShell` between the base wire and the degenerate top wire fails, the
  `except Part.OCCError` branch yields a faces-Compound (or nothing), so the
  result is null/invalid.
- H2: the failure is in `transformShape` (the upper face is null before the
  pipe shell even runs).
- H3: the failure is generic to the Twist path, unrelated to the zero scale.

## Evidence log
- Import probe: cone `[0,0]` → null vol 0; wedge `[0,1]` → null vol 0;
  frustum `[0.5,0.5]` → **valid vol 583.3333**. → H3 REJECTED (non-degenerate
  works; defect is specific to a zero scale component).
- Direct OCC probe: `upper_face` after `transformShape(scale 0)` is **not null**,
  area 0, 4 edges. → H2 REJECTED (transform succeeds; top is a valid but
  zero-area face).
- Same probe: `MakePipeShell.isReady()` True, then `build()` raises
  `OCCError('gp_Dir() - input vector has zero norm')` for both cone and wedge.
  → **H1 ACCEPTED** (degenerate top wire makes the pipe-shell sweep direction
  undefined).
- Construction probe: connecting each base outer-wire vertex to its scaled top
  vertex (triangle where the top degenerates to a point, quad otherwise) +
  bottom cap + top cap when non-degenerate, made into a shell→solid, gives
  exact valid closed solids: cone **333.3333** (=base·h/3), wedge **500.0**
  (=base·h/2), frustum **583.3333** (=h/3·(A0+A1+√(A0A1))). Matches OpenSCAD.

## Verdict
- **H1 ACCEPTED**; H2, H3 REJECTED.
- Fix: in `Twist.execute`, when there is **no twist** (`Angle==0`) and a scale
  component is 0 (degenerate top) and the face is a **single wire** (no holes),
  build the tapered solid analytically by connecting base→scaled-top perimeter
  vertices instead of sweeping a pipe shell. Non-degenerate scale and the
  twist path are untouched. Holed profiles under a zero scale fall through to
  the existing path (documented limitation; the collapsing-hole solid has no
  clean analytic target and is out of this minimal scope).
- Analytic expected: cone (scale 0,0) = base·h/3; wedge (scale 0,1) = base·h/2.
