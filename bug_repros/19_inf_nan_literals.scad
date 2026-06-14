// Compiles to (1/0 -> inf): cylinder($fn=inf, ...); sphere(... r=inf); etc.
// SYMPTOM: every statement containing inf/nan was dropped. stderr showed
//   "syntax error near 'inf' (token ID)" per line, and PLY error recovery
//   discarded the WHOLE statement -- so a finite primitive whose only oddity
//   was $fn=inf vanished, and t3d__primitive-inf-tests.csg imported as nothing
//   where OpenSCAD renders two real solids.
// CAUSE: OpenSCAD emits inf/nan as bare tokens and its CSG reader treats them as
//   an unknown variable -> undef. FreeCAD's lexer (tokrules.py t_ID) tokenised
//   them as identifiers, hitting the grammar where a NUMBER was expected.
// FIX: tokrules.py lexes inf/nan (case-insensitive) as NUMBER so the parser
//   never derails; importCSG.py guards the consumers to match undef semantics:
//   non-finite $fn (circle/cylinder) -> unset -> smooth (int(round(inf)) would
//   also OverflowError); non-finite dimension (square/circle/sphere/cube/
//   cylinder) -> empty; non-finite vertex (polygon/polyhedron, via
//   all_points_finite) -> empty. Commit 61d6b153f3.
// EXPECTED (OpenSCAD): $fn=inf is undef -> default facets -> the cylinder RENDERS
//   smooth, V = pi*r^2*h = pi*9*2 = 18*pi; the inf-radius sphere is EMPTY.
cylinder($fn = 1/0, h = 2, r1 = 3, r2 = 3);
sphere(r = 1/0);
