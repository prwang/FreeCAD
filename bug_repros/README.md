# bug_repros — minimized `.scad` repros, one per fixed importCSG defect

Dev scaffolding, TRACKED on our fork (the `.scad` + this README; the compiled
`out/` stays untracked). Per CLAUDE.md rule 6: each fixed defect
gets a hand-minimized OpenSCAD source that hits the *exact* bug point and a
header comment block (SYMPTOM / CAUSE / FIX / EXPECTED). These are our own
record of what failed and where it was fixed — NOT the PR's regression tests
(those are the inline `utility_create_csg` cases in
`OpenSCADTest/app/test_importCSG.py`).

To reproduce: `openscad -o x.csg NN_slug.scad` then import the `.csg`
(or `git checkout <parent>~1` of the listed commit to see the pre-fix failure).

Numbered in commit order. Commits `3ea6eb73e2` and `bdfcc95a4d` each bundle
several Phase 1–3 defects (one repro per constituent defect).

| # | repro | defect | commit |
|---|---|---|---|
| 01 | `01_intersection_ne2_children.scad` | intersection() with ≠2 children crashed (eager .Base/.Tool) | `3ea6eb73e2` |
| 02 | `02_null_shape_fuse_chain.scad` | null-shape crash chain (checkObjShape no-op + shallow recompute) | `3ea6eb73e2` |
| 03 | `03_boolean_refine_selfintersect.scad` | imported booleans inherited Refine=true → self-intersecting shells | `3ea6eb73e2` |
| 04 | `04_background_modifier_fused.scad` | `%` background subtree fused into the result | `3ea6eb73e2` |
| 05 | `05_circle_double_creation.scad` | circle created twice → orphan visible root | `3ea6eb73e2` |
| 06 | `06_2d_boolean_fragmentation.scad` | 2D boolean imported as fragment tiling → fillet lost | `3ea6eb73e2` |
| 07 | `07_makeoffset_fullcircle_sigsegv.scad` | MakeOffset SIGSEGV on single-edge full-circle wire | `3ea6eb73e2` |
| 08 | `08_offset_childless.scad` | childless `offset(r=1);` had no grammar rule | `bdfcc95a4d` |
| 09 | `09_offset_background_only.scad` | offset with all children dropped → None deref | `bdfcc95a4d` |
| 10 | `10_offset_3d_child.scad` | offset of a 3D child → TypeError | `bdfcc95a4d` |
| 11 | `11_circle_fractional_fn.scad` | `circle($fn=0.1)` → `int('0.1')` ValueError | `bc822b9446` |
| 12 | `12_resize_zero_extent_axis.scad` | `resize()` of a zero-extent axis → ZeroDivisionError | `eb2c64eb66` |
| 13 | `13_rotate_extrude_childless.scad` | childless `rotate_extrude()` → KeyError 'file' | `12cbeaa3b2` |
| 14 | `14_intersection_empty_operand.scad` | `intersection()` with a null operand → "Null input shape" | `3d58052896` |
| 15 | `15_square_non_positive.scad` | non-positive `square()` → degenerate plane (vol 107 vs 7) | `bf901fb45e` |
| 16 | `16_polygon_multipath_holes.scad` | multi-path `polygon()` dropped holes (kept only last path) | `c5b73a415d` |
| 17 | `17_polygon_points_undef.scad` | `polygon(points=undef)` → syntax error; p_error silent | `205a619b6a` |
| 18 | `18_fuse_extrude_null_propagation.scad` | null operand propagated through extrude/MultiFuse → null union | `024eff9443` |
| 19 | `19_inf_nan_literals.scad` | `inf`/`nan` literals lexed as ID → statement dropped | `61d6b153f3` |
| 20 | `20_linear_extrude_scale_taper.scad` | `linear_extrude(scale=0)` taper → null shape (pipe-shell zero-norm) | `ff880cd47a` |
| 21 | `21_projection_cut_false_plane_leak.scad` | `projection(cut=false)` leaked `xy_plane_used_for_projection` orphan root | `3ba221ab68` |
| 22 | `22_multmatrix_scale_source_leak.scad` | non-rigid `multmatrix` leaked untransformed source as orphan root | `ac08e5e2c5` |
| 23 | `23_resize_source_leak.scad` | `resize()` leaked un-resized source child as orphan root (double-count) | `b8a90c6d93` |
| 24 | `24_linear_extrude_twist_scale_zero.scad` | `linear_extrude(twist, scale=[0,0])` point-collapse → null (gp_Dir zero norm) | `8e36697899` |
| 25 | `25_resize_negative_newsize.scad` | `resize()` negative newsize scaled by negative ratio (mirror) instead of unchanged | `561edf6ebe` |
| 26 | `26_resize_auto_scale.scad` | `resize()` auto-scale used X target / clobbered explicit axis (≠ OpenSCAD max-factor rule) | `07d36bceee` |
| 27 | `27_linear_extrude_twist_line_collapse.scad` | `linear_extrude(twist=180, scale=[0,1])` single-wire line-collapse → null (MakePipeShell) | `<pending>` |
