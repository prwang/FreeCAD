// SYMPTOM: ex__module_recursion (a 16376-line fractal tree of 2047 overlapping
//   colored square()s) aborted the WHOLE import at parse with
//   `CADKernelError: Invalid input shape for boolean FUS: Unorientable shape`,
//   raised by the eager 2-operand fuse `Base.Shape.fuse(Tool.Shape)` in fuse()
//   (Category C: a hard crash, no STEP produced).
// CAUSE: over the whole model EXACTLY ONE fuse fails. Its tool operand is a
//   single 2D face accumulated from a long chain of unions of overlapping
//   rectangles (38 wires / 991 edges) that came out geometrically INVALID
//   (mis-oriented inner wires). OCC cannot orient an invalid operand and aborts
//   the exact boolean. (Confirmed by instrumenting fuse(): base valid=True,
//   tool valid=False; a fuzzy-tolerance retry did NOT help, but rebuilding the
//   face did.)
// FIX: importCSG.py -> add repair2DFaces() (ShapeFix on a mutable copy, which
//   reorients the wires and PRESERVES holes; falls back to the outer boundary
//   only if ShapeFix fails) and wrap the single-fuse in try/except: on failure
//   repair both operands and retry, baking the result into a static
//   Part::Feature (and consuming the two child subtrees) so the final recompute
//   does not re-run the failing parametric boolean. If the retry still fails the
//   original error propagates (no masking of unrelated bugs). Commit <C5-HASH>.
// EXPECTED (OpenSCAD): the union renders as one valid 2D region. After the fix
//   the "Unorientable" crash is gone; ex__module_recursion no longer aborts at
//   parse. (It is also a very heavy model -- 2047 nested booleans -- so it may
//   still exceed the corpus 300s budget and land as a Priority-C timeout; that
//   is an honest resource limit, not the crash.)
// NOTE: the emergent invalid multi-wire face has no faithful minimal .scad form
//   (OpenSCAD never emits a mis-oriented polygon). The DETERMINISTIC minimal
//   reproduction is the unit test test_repair_invalid_2d_face_for_fuse, which
//   builds a Part.Face([outer, inner]) with a non-reversed inner wire (invalid,
//   area 136) that fails fuse(), and asserts repair2DFaces() returns a valid
//   face of area 64 (hole preserved) that fuses cleanly. The fan of overlapping
//   rotated rectangles below is the closest expressible witness to the canopy
//   motif that produces such faces.
for (a = [0 : 8 : 176])
	rotate([0, 0, a])
		translate([0, 20, 0])
			square([4, 40], center = true);
