// SYMPTOM: AttributeError dereferencing a None source.
// CAUSE: the '%' background child is removed from the document (background-
//   modifier fix, repro 04), so the offset's only child was dropped and the
//   offset then dereferenced a None source. (Reachable only after the
//   background fix existed.)
// FIX: importCSG.py -> an offset whose children were all dropped yields an
//   empty result instead of dereferencing None. Commit bdfcc95a4d.
// EXPECTED (OpenSCAD): the '%' subtree is preview-only and contributes no
//   geometry, so the offset has nothing to offset -> empty. No crash.
offset(r = 1) %circle(r = 5);
