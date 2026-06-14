// SYMPTOM: a real union imported as ALL-NULL roots (jbarr routing_tiles, a
//   51-volume model, came back as 84 null Part::Feature roots). Before the
//   square fix (#15) it was a "Null input shape" CRASH instead.
// CAUSE: square([0,0]) imports as a null-shape operand (#15, so intersection
//   stays correct). That null then propagated through two consumers that were
//   never null-safe: linear_extrude (a null profile -> null Part::Extrusion)
//   and the >2-child Part::MultiFuse (recomputes to a null shape), nulling the
//   whole union.
// FIX: importCSG.py -> fuse() resolves lazy shapes, then DROPS and CONSUMES
//   null operands up front (A u 0 = A; replaces the single-fuse special case);
//   linear_extrude of a null/empty profile returns empty and consumes the
//   profile (extrude(0) = 0) so no stray null root lingers. Commit 024eff9443.
// EXPECTED (OpenSCAD): the empty extrude contributes nothing; the three disjoint
//   cubes survive -> volume 3*1000 = 3000, and NO null document roots.
union() {
	cube([10, 10, 10]);
	translate([20, 0, 0]) cube([10, 10, 10]);
	translate([40, 0, 0]) cube([10, 10, 10]);
	linear_extrude(height = 2) square([0, 0]);
}
