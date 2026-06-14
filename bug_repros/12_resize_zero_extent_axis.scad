// SYMPTOM: import aborted during parse with ZeroDivisionError.
// CAUSE: p_resize_action built the scale matrix as new_size[r]/old_size[r] per
//   axis. A 2D shape has ZLength 0, so the Z term divided by zero. (resize to
//   [15,15,0] on a 10x10 square: the Z axis has old extent 0.)
// FIX: importCSG.py p_resize_action -> factor 1.0 for any zero-extent axis
//   (a zero-extent axis cannot be stretched; OpenSCAD leaves it unchanged).
//   Commit eb2c64eb66.
// EXPECTED (OpenSCAD): the 10x10 square stretches to 15x15 (area 225); Z
//   unchanged. No crash.
resize([15, 15, 0]) square([10, 10]);
