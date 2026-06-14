// SYMPTOM: a non-rigid (scaling/shear) multmatrix left the UNTRANSFORMED source
//   object as a stray orphan document root, so a scaled solid appeared twice --
//   once raw, once transformed. Discovered via polyhedron-nonplanar-tests: a
//   120-point polyhedron under a 0.02 scale imported as TWO roots, the correct
//   scaled result (vol 1.654) AND a leaked raw copy (vol 206803), wrecking the
//   total (206806 vs OpenSCAD 2.943).
// CAUSE: importCSG.p_multmatrix_action has three transform paths. The rigid
//   path reuses `part` (updates its Placement) and the MatrixTransform path
//   links `part` via obj.Base, so both keep the source non-root. The
//   transformGeometry fallback (the useMultmatrixFeature==False branch, which
//   is the headless default) bakes part.Shape.transformGeometry(M) into a new
//   Part::Feature but never consumed `part` -> orphan root.
// FIX: importCSG.py p_multmatrix_action -> after baking the transformed shape,
//   remove `part` and its subtree (OutListRecursive) from the document; its
//   geometry is fully copied into new_part and nothing else references it.
//   Commit ac08e5e2c5.
// EXPECTED (OpenSCAD): scaling a 10x10x10 cube by 2 in every axis is one solid
//   of volume 10^3 * 2^3 = 8000 -- exactly ONE document root, no leftover
//   1000-unit raw cube. (The polyhedron geometry itself was already correct;
//   this is the multmatrix leak that nonplanar-tests surfaced.)
multmatrix([[2, 0, 0, 0], [0, 2, 0, 0], [0, 0, 2, 0], [0, 0, 0, 1]])
	cube([10, 10, 10]);
