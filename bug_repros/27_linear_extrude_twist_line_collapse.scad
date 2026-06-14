// SYMPTOM: a twisted linear_extrude whose top collapses to a LINE (exactly one
//   zero scale component) imported as a NULL shape for some twist angles --
//   e.g. twist=180, scale=[0,1] square([2,2]). Asymmetric: scale=[1,0]+twist180
//   and scale=[0,1]+twist90 both built fine. The twist=180 [0,1] null was the
//   remaining contributor to t3d__linear_extrude-scale-zero-tests (single-wire
//   variants). (A5 had fixed only the both-zero POINT collapse with twist.)
// CAUSE: OpenSCADFeatures.Twist.execute. The general path sweeps the profile
//   with MakePipeShell + an auxiliary helix; for some twisted line collapses
//   pipe_shell.isReady()/build() raise, and the face loop aborted before
//   fp.Shape was set -> null.
// FIX: OpenSCADFeatures.py Twist.execute -> build the sweep defensively; when it
//   RAISES (only then) and the profile is a single-wire one-zero (line) twisted
//   case, fall back to _twisted_taper_solid, which lofts through the
//   rotated+scaled cross-sections (one slice per ~9 deg of twist). The success
//   path and the Shell/Solid OCCError->Compound fallback are unchanged, so the
//   many working twist cases are untouched. A holed/multi-wire twisted
//   taper-to-line self-intersects and has no clean OCC solid -> left empty
//   (not forced into an invalid shape that would poison unions). Commit <pending>.
// EXPECTED (OpenSCAD): twist preserves cross-sectional area, so the smooth wedge
//   volume is base*h/2 = 2*2*3/2 = 6. OpenSCAD's 20-slice render is 6.106 and
//   the discretized loft slightly overshoots (~6.4) -- faceting-class; the point
//   is the geometry is a valid solid, no longer dropped to null.
linear_extrude(height = 3, twist = 180, slices = 20, scale = [0, 1])
	square([2, 2]);
