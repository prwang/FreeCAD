# CURRENT BUG — A3#8 polyhedron (resolved to: non-rigid multmatrix orphan leak)

## Observation
- Family: t3d__polyhedron-* (plan flagged "polyhedron-tests 50 % / nonplanar
  7e6 %").
- Probes over the whole corpus polyhedron set:
  - polyhedron-cube → vol 1.0 (unit cube) ✓
  - polyhedron-concave → vol 340.0 (= hexagon area 68 × h 5) ✓
  - polyhedron-soup (triangle soup, duplicated vertices, octahedron) → 4/3 ✓
  - polyhedron-tests (octahedra incl. inconsistent winding) → all valid ✓
  - polyhedron-nonplanar-tests → total **206806** vs OpenSCAD ref **2.943**.
- Decomposing nonplanar-tests by root:
  - root0 polyhedron (near-unit-cube, slightly non-planar) = 1.0 (== OpenSCAD)
  - root1 polyhedron001 (giant 120-pt spiky, RAW/untransformed) = **206803**
  - root2 Matrix_Deformation (the giant after its 0.02 scale) = **1.654**
  - root3 polyhedron002 = 0.289
  - OpenSCAD ref total 2.943 = 1.0 + 1.654 + 0.289 (root1 is spurious).

## Hypotheses (each independently testable)
- H1: polyhedron face building (makeFilledFace on non-planar faces, or
  winding) is wrong → bad geometry.
- H2: the giant's TRANSFORMED result is wrong (makeFilledFace bulge).
- H3: a non-rigid (scaling/shear) multmatrix leaves its untransformed source
  `part` as an orphan document root, so the giant polyhedron appears twice:
  once raw (206803) and once correctly scaled (1.654).

## Evidence log
- cube/concave/soup/tests/octahedra all match analytic targets, incl. the
  inconsistent-winding octahedron (Part.makeShell sews by shared geometry, so
  winding is tolerated). → **H1 REJECTED**.
- root2 Matrix_Deformation = 1.654 == (OpenSCAD ref 2.943 − 1.0 − 0.289). The
  transformed giant is correct. → **H2 REJECTED**.
- InList probe: root1 polyhedron001 has InList=0 (parentless ROOT), and
  Matrix_Deformation is a plain Part::Feature (path 4, transformGeometry), NOT
  a FeaturePython linking the source. p_multmatrix_action path 4 (importCSG.py
  ~1162-1170, the `useMultmatrixFeature`==False branch, which is the headless
  default) bakes `part.Shape.transformGeometry(M)` into a new Part::Feature but
  never consumes `part`; paths 1 (rigid) and 3 (MatrixTransform `obj.Base`
  link) keep the source non-root. → **H3 ACCEPTED**.
- Dev corpus uses only rotation multmatrices (orthogonal → path 1), so it never
  hit this leak — hence 35/35 MATCH despite the bug; the fix won't regress it.

## Verdict
- **H3 ACCEPTED**; H1, H2 REJECTED. The polyhedron builder is correct; the
  defect is the multmatrix transformGeometry path leaking its untransformed
  source as a stray orphan root under any non-rigid (scaling/shear) matrix.
- Fix: in p_multmatrix_action path 4, after baking the transformed shape into
  `new_part`, remove the now-redundant `part` and its subtree from the
  document (its geometry is fully copied into new_part; it is referenced by
  nothing).
- Analytic expected: `multmatrix(scale 2) cube(10)` → exactly ONE root,
  vol 8000 (10³·2³), with no leftover raw 1000 cube.
