// SYMPTOM: offset() of an empty/degenerate 2D region aborted the WHOLE import.
//   t2d__offset-tests ends with `offset(r=1) square([0,0]);`; the import died at
//   parse with `RuntimeError: shape is invalid`, losing all 20+ valid offset
//   results in the file (Category C: a hard error, no STEP produced).
// CAUSE: square([0,0]) is non-positive, so p_square_action builds a NULL shape
//   (Part.Shape(), the bf901fb45e degenerate-square fix). p_offset_action then
//   read `subobj.Shape.Volume` unconditionally (importCSG.py ~L453); .Volume on
//   a null shape raises "shape is invalid". The childless-offset guard above
//   (len(p[6])==0) does not catch a present-but-null child.
// FIX: importCSG.py p_offset_action -> add a `subobj.Shape.isNull()` guard
//   BEFORE the .Volume test: consume the subtree and render empty (offsetting an
//   empty region yields nothing), matching the childless and 3D-child paths.
//   Commit 39eebb0263.
// EXPECTED (OpenSCAD): offset() of an empty 2D region is empty; it does not abort
//   the model. Sibling geometry (here cube([3,3,3]), volume 27) is unaffected.
offset(r = 1)
	square([0, 0]);
cube([3, 3, 3]);
