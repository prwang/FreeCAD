// SYMPTOM: imported booleans came back as self-intersecting / invalid shells;
//   STEP export then failed or produced bad geometry.
// CAUSE: importer booleans inherited the Mod/Part preference RefineModel=true,
//   so removeSplitter ran and turned OpenSCAD's tangent / near-coincident faces
//   (common where parts butt together) into self-intersecting shells.
// FIX: importCSG.py -> new addBoolean() helper creates EVERY importer boolean
//   with Refine=False (no removeSplitter). Commit 3ea6eb73e2.
// EXPECTED (OpenSCAD): two unit cubes meeting on the tangent plane x=10 union
//   into one valid solid of volume 2000 (no self-intersection).
union() {
	cube([10, 10, 10]);
	translate([10, 0, 0]) cube([10, 10, 10]);
}
