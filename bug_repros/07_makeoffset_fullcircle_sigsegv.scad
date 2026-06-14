// SYMPTOM: hard SIGSEGV (process crash, not a Python exception) inside
//   BRepOffsetAPI_MakeOffset, when offsetting a wire that is a single-edge full
//   circle -- as produced by offsetting a circular hole.
// CAUSE: OCC's MakeOffset cannot handle a closed wire made of one full-circle
//   edge.
// FIX: OpenSCADFeatures.py UnifyFaces.splitFullCircles -> rebuild a single-edge
//   full-circle wire as TWO half-circle arcs before offsetting. Commit
//   3ea6eb73e2.
// EXPECTED (OpenSCAD): offsetting a square-with-a-circular-hole grows the outer
//   boundary and shrinks the hole, producing a valid region -- no SIGSEGV. The
//   circular hole's wire is the single-edge full circle that triggered it.
offset(r = 1) difference() {
	square([20, 20], center = true);
	circle(r = 5);
}
