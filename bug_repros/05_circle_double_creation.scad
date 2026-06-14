// SYMPTOM: each smooth circle created TWO objects; the manually-built one was
//   shadowed by a second Draft.makeCircle() and leaked as a visible orphan
//   document root (seen in 18/31 corpus cases).
// CAUSE: p_circle_action built the circle object AND then also called
//   Draft.makeCircle(), creating a duplicate.
// FIX: importCSG.py p_circle_action -> build the Draft._Circle object once; do
//   NOT also call Draft.makeCircle(). Commit 3ea6eb73e2.
// EXPECTED (OpenSCAD): one circle -> exactly ONE document root (area pi*100),
//   no orphan.
circle(r = 10);
