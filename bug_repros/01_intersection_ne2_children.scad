// SYMPTOM: intersection() with a number of children != 2 crashed during import
//   (AttributeError: the eager .Shape compute read .Base/.Tool).
// CAUSE: p_intersection_action computed the result eagerly assuming .Base/.Tool,
//   which only the 2-child Part::Common branch has -- the >2-child
//   Part::MultiCommon (and the 0/1-child cases) do not.
// FIX: importCSG.py -> move the eager .Shape compute INTO the 2-child branch,
//   mirroring fuse() (and the difference fix in 2c6af06fe96). Commit 3ea6eb73e2.
// EXPECTED (OpenSCAD): a 3-way intersection is the common overlap of all three.
//   Here three 10x10 squares stepped by 2 overlap on a 6x6 region -> area 36.
intersection() {
	square([10, 10]);
	translate([2, 2]) square([10, 10]);
	translate([4, 4]) square([10, 10]);
}
