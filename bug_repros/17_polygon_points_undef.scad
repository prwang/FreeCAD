// Compiles to: polygon(points = undef, paths = undef, convexity = 1);
// SYMPTOM: matched NO grammar rule -> syntax error. Worse, p_error printed only
//   under printverbose, so the import came back mysteriously empty/partial with
//   no diagnostic. OpenSCAD emits points=undef pervasively for empty polygons
//   in Round-Anything library code.
// CAUSE: (a) no production for polygon(points=undef, paths=undef);
//   (b) p_error swallowed syntax errors silently.
// FIX: importCSG.py -> add p_polygon_action_undef rule that imports it as an
//   empty result (it has no geometry); p_error now prints a Console error
//   naming the token + line, then lets PLY resynchronise so the rest imports.
//   Commit 205a619b6a.
// EXPECTED (OpenSCAD): polygon() renders nothing; a sibling cube still imports;
//   NO syntax error fires.
union() {
	polygon();
	cube([10, 10, 10]);
}
