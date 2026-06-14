// SYMPTOM: 2D booleans imported as a TILING OF FRAGMENT FACES instead of one
//   region face; an offset(-r) offset(+r) fillet was silently lost (the rounded
//   corner fragments were dropped).
// CAUSE: importCSG used OCC's general fuse for 2D booleans, which leaves the
//   result as separate fragment faces rather than a unified region.
// FIX: importCSG.py + OpenSCADFeatures.py -> new UnifyFaces FeaturePython proxy
//   re-fuses fragments into whole faces; importCSG wraps every 2D boolean result
//   and every 2D offset() source with it. Commit 3ea6eb73e2.
// EXPECTED (OpenSCAD): the union of two overlapping squares is a single L-shaped
//   region. Two 10x10 squares offset by [5,5] overlap on 5x5 -> area
//   100 + 100 - 25 = 175, as ONE face (not a fragment tiling).
union() {
	square([10, 10]);
	translate([5, 5]) square([10, 10]);
}
