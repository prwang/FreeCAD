// SYMPTOM: projection(cut=false) left a stray "xy_plane_used_for_projection"
//   Part::Plane (a ~bbox-sized face) as an orphan document root, polluting the
//   imported result with a phantom rectangle. The true-projection result itself
//   is an (intentional) unsupported placeholder, so the leftover plane was the
//   only visible geometry the cut=false branch contributed.
// CAUSE: importCSG.p_projection_action built the helper cutting plane (and the
//   bbox work that sizes it) UNCONDITIONALLY, but only the cut=true branch
//   consumes it (into a Part::MultiCommon). On the cut=false path nothing ever
//   referenced the plane, so it lingered as a top-level root.
// FIX: importCSG.py p_projection_action -> build the plane + bbox inside the
//   cut=true branch only. cut=true geometry is unchanged; cut=false no longer
//   leaks a plane. True shadow projection stays a placeholder (no clean OCC /
//   analytic target -- honestly out of scope). Commit <pending>.
// EXPECTED (OpenSCAD): projection(cut=true) of a centered cube is the 10x10
//   mid-section (area 100); projection(cut=false) is the silhouette. Either way
//   the importer must NOT emit a stray xy_plane_used_for_projection root.
projection(cut = false) cube([10, 10, 10], center = true);
