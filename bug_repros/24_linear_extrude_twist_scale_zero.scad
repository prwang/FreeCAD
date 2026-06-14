// SYMPTOM: linear_extrude with BOTH a twist and a scale whose top collapses to
//   a POINT (scale=[0,0]) imported as a NULL shape (stage=invalid-shape, "all
//   root shapes are null"). The one-zero (line) collapse, e.g. scale=[0,1], was
//   NOT affected -- it already built a valid solid. Drove corpus
//   t3d__linear_extrude-scale-zero-tests (44.8 %) and ex__linear_extrude (24 %).
// CAUSE: OpenSCADFeatures.Twist.execute. The A2#6 degenerate-taper branch (which
//   builds the tapered solid analytically by joining base perimeter vertices to
//   their scaled top vertices) was gated on `fp.Angle.Value == 0.0`. With a twist
//   the point-collapse case skipped that branch and fell through to MakePipeShell
//   between the base wire and the zero-area point top, whose sweep direction is
//   undefined -> "gp_Dir() - input vector has zero norm" -> null shape.
// FIX: OpenSCADFeatures.py Twist.execute -> take the analytic _taper_solid path
//   whenever the top collapses to a point (abs(sx)<eps AND abs(sy)<eps),
//   regardless of the twist angle, keeping the no-twist one-zero (line) branch
//   and leaving the twist+line case on its working MakePipeShell path. A point
//   apex lies ON the twist axis, so the twist leaves it invariant: the solid is
//   exactly the straight pyramid. Commit <pending>.
// EXPECTED (OpenSCAD): twist preserves cross-sectional area, so the volume equals
//   the no-twist value. A 2x2 base extruded h=3 tapering to a point (scale=[0,0])
//   is a pyramid of base*h/3 = 4*3/3 = 4 (OpenSCAD's 20-slice render is 4.087, a
//   2.1 % discretization overshoot above the smooth limit -- faceting-class).
linear_extrude(height = 3, twist = 180, slices = 20, scale = [0, 0])
	square([2, 2]);
