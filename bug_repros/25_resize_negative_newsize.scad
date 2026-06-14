// SYMPTOM: resize() with a NEGATIVE newsize component scaled that axis by the
//   negative ratio, producing a mirrored/oversized solid. resize([-5,0,0])
//   cube([1,1,1]) imported as a volume-5 solid (X factor -5) instead of the unit
//   cube. A contributor (alongside the auto-on-explicit-axis UNKNOWN) to the
//   t3d__resize-tests residual.
// CAUSE: importCSG.p_resize_action guarded the "leave this axis unchanged" case
//   with an exact string compare `if new_size[r] == '0'`. A negative target
//   formats as e.g. '-5', never equals '0', so it fell through to
//   factor = float('-5')/old_size = -5 -> Matrix.scale(-5,1,1) -> mirrored cube.
// FIX: importCSG.py p_resize_action -> replace the `== '0'` guard with a numeric
//   `float(new_size[r]) <= 0` test, so 0, 0.0 and negatives all leave that axis
//   unchanged (factor 1.0). Commit 561edf6ebe.
// EXPECTED (OpenSCAD): a newsize <= 0 means "do not resize this axis" -- it is
//   NOT a mirror. resize([-5,0,0]) cube([1,1,1]) renders as the original unit
//   cube, volume 1 (verified by openscad STL render = 1.0).
resize([-5, 0, 0])
	cube([1, 1, 1]);
