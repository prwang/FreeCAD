// SYMPTOM: linear_extrude() with a scale that has a ZERO component imported as
//   a NULL shape (volume 0). OpenSCAD bakes scale=0 -> scale=[0,0] (taper to a
//   point) and scale=[0,1] tapers to a line. Non-zero scale (a frustum) was
//   already fine, so the whole solid silently vanished only for the taper case.
// CAUSE: OpenSCADFeatures.Twist.execute sweeps a Part.BRepOffsetAPI.MakePipeShell
//   between the base wire and the scaled top wire. A zero scale component makes
//   the top wire a zero-area line/point, so the sweep direction is undefined and
//   build() raises OCCError("gp_Dir() - input vector has zero norm"); the
//   except-branch left fp.Shape null.
// FIX: OpenSCADFeatures.py Twist.execute + new Twist._taper_solid /
//   Twist._planar_faces -> when there is no twist (Angle==0), a scale component
//   is 0, and the profile is a single wire, build the tapered solid by
//   connecting each base perimeter vertex to its scaled top vertex (side is a
//   triangle where the top collapses to a point, a quad otherwise; no top cap).
//   The pipe-shell path (twist, non-degenerate scale, curved single-vertex
//   profiles like circle) is untouched. Commit ff880cd47a.
// EXPECTED (OpenSCAD): a 10x10 base extruded h=10 -->
//   scale=[0,0] pyramid  = base*h/3 = 1000/3 = 333.333
//   scale=[0,1] wedge    = base*h/2 = 500
//   scale=[0.5,0.5] frustum = h/3*(A0+A1+sqrt(A0*A1)) = 10/3*(100+25+50) = 583.333
linear_extrude(height = 10, scale = 0) square([10, 10]);
