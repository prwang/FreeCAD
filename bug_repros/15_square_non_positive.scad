// SYMPTOM: a square with a non-positive dimension imported as a DEGENERATE
//   Part::Plane (Length/Width <= 0) -- an invalid or bogusly non-empty face.
//   In the square-tests corpus case this measured volume 107 vs the reference 7.
// CAUSE: p_square_action built Part::Plane unconditionally; OpenSCAD renders
//   square([x,y]) with x<=0 or y<=0 as EMPTY.
// FIX: importCSG.py p_square_action -> build a null-shaped operand for a
//   non-positive square. It is kept as an operand (not dropped) so set algebra
//   stays correct: visible to intersection (A n 0 = 0). fuse()'s single-fuse
//   branch drops a null operand and passes the other through (A u 0 = A) instead
//   of calling Shape.fuse() on a null. Commit bf901fb45e.
// EXPECTED (OpenSCAD): a 2x3 square unioned with a 1x0 (empty) square -> area 6.
union() {
	square([2, 3]);
	square([1, 0]);
}
