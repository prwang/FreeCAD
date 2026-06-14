// SYMPTOM: TypeError -- a 3D child hit the unfinished
//   subobj[0].Shape.makeOffset branch.
// CAUSE: offset() is 2D-only in OpenSCAD ("Ignoring 3D child object for 2D
//   operation"), but importCSG attempted a 3D offset extension on a 3D child.
// FIX: importCSG.py -> warn, remove the consumed 3D subtree, and yield an empty
//   result (rather than diverge from ground truth with a 3D offset). Commit
//   bdfcc95a4d.
// EXPECTED (OpenSCAD): offset of a 3D child renders empty (with a warning). No
//   crash.
offset(r = 1) cube([10, 10, 10]);
