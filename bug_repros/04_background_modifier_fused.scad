// SYMPTOM: a '%' background subtree (preview-only in OpenSCAD, NOT part of the
//   rendered result) was fused into the imported geometry, inflating it.
// CAUSE: importCSG kept and fused the background-modified child like any other.
// FIX: importCSG.py -> '%' background subtrees are removed from the document so
//   they do not contribute to the result. Commit 3ea6eb73e2.
// EXPECTED (OpenSCAD): the '%' cube is preview-only -> the rendered result is
//   just the first cube, volume 1000 (NOT 2000).
union() {
	cube([10, 10, 10]);
	%translate([20, 0, 0]) cube([10, 10, 10]);
}
