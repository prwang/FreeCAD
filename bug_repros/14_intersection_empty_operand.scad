// SYMPTOM: import aborted during parse with "Null input shape" (OCC) from
//   Base.Shape.common(Tool.Shape).
// CAUSE: p_intersection_action computed common() eagerly; a degenerate operand
//   such as square([0,0]) has a null shape, and OCC's common() rejects a null
//   input. (square([0,0]) is the null operand here.)
// FIX: importCSG.py p_intersection_action -> after resolving lazy shapes
//   (checkObjShape), detect a null operand up front and return an empty result.
//   It must NOT pass the surviving operand through: A n 0 = 0, not A.
//   Commit 3d58052896.
// EXPECTED (OpenSCAD): circle intersect empty = empty. No crash.
intersection() {
	circle(r = 10);
	square([0, 0]);
}
