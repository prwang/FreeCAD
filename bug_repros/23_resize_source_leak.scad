// SYMPTOM: resize() left the un-resized SOURCE child as a stray orphan document
//   root, so the source and the resized result both survived and the summed
//   solids double-counted. With a large source extent the leak dominated the
//   total: corpus t3d__resize-tests blew up by ~4e9 % and t2d__resize-2d-tests
//   by ~40650 %. Minimal: resize([4,0,0]) cube([2,2,2]) imported as TWO roots,
//   the correct Matrix_Deformation (vol 16) AND a leaked raw cube (vol 8).
// CAUSE: importCSG.p_resize_action bakes the resized shape into a new
//   Part::FeaturePython ("Matrix Deformation") via transformGeometry, but only
//   p[6][0].ViewObject.hide()'d the source child -- and only under `gui`.
//   Headless (the importer's default) never consumed the source, leaving it as
//   an orphan root. Same orphan-leak class as the multmatrix fix (ac08e5e2c5),
//   which did not touch resize's separate transform block.
// FIX: importCSG.py p_resize_action -> after baking new_part.Shape, remove
//   p[6][0] and its subtree (OutListRecursive) from the document; its geometry
//   is fully copied into new_part and nothing else references it. Commit
//   b8a90c6d93.
// EXPECTED (OpenSCAD): resize([4,0,0]) scales X from 2 to 4 and leaves Y,Z at 2
//   (a 0 newsize component means "leave that axis unchanged"), giving exactly
//   ONE solid of volume 4*2*2 = 16 -- no leftover 8-unit raw cube.
resize([4, 0, 0])
	cube([2, 2, 2]);
