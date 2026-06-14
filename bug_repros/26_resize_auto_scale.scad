// SYMPTOM: resize() with auto-scaling diverged from OpenSCAD whenever an auto
//   axis had newsize 0 (or when an axis was BOTH auto AND had its own explicit
//   newsize). e.g. resize([5,0,20], auto=[false,true,true]) cube([9,9,9])
//   imported as volume 125 (5x5x5) instead of OpenSCAD's 2000 (5x20x20). The
//   dominant residual of t3d__resize-tests / t2d__resize-2d-tests. Previously
//   mis-parked as "implementation-defined / UNKNOWN" -- it is NOT: OpenSCAD's
//   rule is concrete and deterministic.
// CAUSE: importCSG.p_resize_action did `if auto[r]: new_size[r] = new_size[0]`,
//   i.e. it set every auto axis's target to the X target value, and clobbered an
//   axis that already had an explicit newsize. OpenSCAD instead scales each auto
//   axis by an "autoscale" factor = the MAX of the explicit per-axis factors.
// FIX: importCSG.py p_resize_action -> compute factor[i]=newsize[i]/old[i] for
//   axes with newsize>0; autoscale = max of those; an auto axis with newsize 0
//   takes autoscale; non-auto newsize<=0 and zero-extent axes stay unchanged.
//   Commit 07d36bceee.
// EXPECTED (OpenSCAD 2021.01, verified by STL render on cube([9,9,9])):
//   [5,0,0]  auto[T,T,F] -> 5,5,9   = 225  (y follows x's 5/9)
//   [5,0,20] auto[F,T,T] -> 5,20,20 = 2000 (y follows max(5/9,20/9)=20/9; z=20)
//   [6,0,0]  auto[T,T,T] -> 6,6,6   = 216  (uniform)
resize([5, 0, 20], auto = [false, true, true])
	cube([9, 9, 9]);
