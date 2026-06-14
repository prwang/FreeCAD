// Compiles to: offset(r = 1, ...);  (both `offset(r=1);` and `offset(r=1){}`
//   compile to this childless semicolon form.)
// SYMPTOM: no grammar rule matched -> silent parse error (relied on yacc error
//   recovery), giving a mysteriously empty/partial document.
// CAUSE: importCSG had no production for a childless offset().
// FIX: importCSG.py -> add an explicit empty production (p_offset_empty_action).
//   Commit bdfcc95a4d.
// EXPECTED (OpenSCAD 2021.01): a childless offset renders empty. No parse error.
offset(r = 1);
