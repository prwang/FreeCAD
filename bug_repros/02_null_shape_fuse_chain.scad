// SYMPTOM: ValueError: Null input shape, raised inside fuse().
// CAUSE: two compounding gaps. (a) checkObjShape silently no-op'd on the LISTS
//   that single-child groups pass it (it expected a document object, not a
//   list), so it never validated/recomputed them. (b) its single-level
//   recompute could not resolve a lazy dependency chain (Offset2D feeding an
//   extrusion feeding a boolean) -- the operand shapes were still null when
//   fuse() called Shape.fuse() on them.
// FIX: importCSG.py checkObjShape -> flatten lists and recompute RECURSIVELY so
//   lazy Offset2D/extrusion chains resolve before any boolean. Commit 3ea6eb73e2.
// EXPECTED (OpenSCAD): the two offset() regions union into one valid shape (no
//   null operand reaches the fuse). Representative of the driving corpus chain;
//   the point is "no Null input shape crash", with a finite unified area.
union() {
	offset(r = 1) square([10, 10]);
	offset(r = 1) translate([20, 0]) square([10, 10]);
}
