// SYMPTOM: a polygon with an outer boundary plus hole path(s) imported as just
//   the LAST sub-path -- the holes were silently lost.
// CAUSE: p_polygon_action_plus_path looped over the paths, built a separate
//   Part.Face per path, and assigned p[0] = [mypolygon] from INSIDE the loop
//   (the code's own comment: "This only pushes last polygon").
// FIX: importCSG.py p_polygon_action_plus_path -> build one face: largest wire
//   as the outer boundary, cut the remaining wires as holes (boolean cut is
//   orientation-independent, where Part.Face([outer, inner]) would have ADDED
//   the inner area). Commit c5b73a415d.
// EXPECTED (OpenSCAD): a 10x10 polygon with a centered 4x4 hole path fills by
//   the even-odd rule -> one face, area 100 - 16 = 84, two wires.
polygon(
	points = [[0,0],[10,0],[10,10],[0,10], [3,3],[7,3],[7,7],[3,7]],
	paths  = [[0,1,2,3], [4,5,6,7]]);
