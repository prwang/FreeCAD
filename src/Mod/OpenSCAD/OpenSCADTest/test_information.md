# OpenSCAD Unit Test Information

The OpenSCAD testing framework is based on the tests in the FEM Module.

## Running

```sh
# whole module suite (registered in Init.py when an openscad executable is configured):
FreeCADCmd -t TestOpenSCADApp
# importCSG tests directly (works without the registration):
FreeCADCmd -t OpenSCADTest.app.test_importCSG
# single test:
FreeCADCmd -t OpenSCADTest.app.test_importCSG.TestImportCSG.test_import_sphere
```

Tests that import `.scad` sources call the OpenSCAD executable
(`Mod/OpenSCAD` preference `openscadexecutable`); tests built on the
`utility_create_csg` helper parse hand-written `.csg` text directly and run
without it.

## Structure

* `app/test_importCSG.py` — importer tests. Static fixtures live in
  `data/` (resolved via `FreeCAD.getHomePath()`), inline fixtures are
  written to a temp dir by `utility_create_scad` / `utility_create_csg`.
* `data/` — fixture files; new files must be added to
  `OpenSCADTestsFiles_SRCS` in `src/Mod/OpenSCAD/CMakeLists.txt`.
* `gui/` — GUI test placeholder.

## Regression groups in test_importCSG.py

Beyond the primitive/transform import tests, the suite carries regression
tests for importer bugs found by the offline conversion harness
(`src/Mod/OpenSCAD/csg_isolation/README.md` documents the bugs and the harness):

* `test_import_intersection_*` — `intersection()` child-count handling
  (the eager `.Shape` compute used to crash for ≠ 2 children).
* `test_import_fuse_of_offset_extrusions` — null-shape crash chain through
  lazy `offset()`/extrusion dependencies (minimized real-world repro).
* `test_import_background_modifier` / `test_import_debug_modifier` — `%`
  subtrees are excluded from the result; `#` subtrees are kept.
* `test_import_booleans_unrefined` — imported booleans must not inherit
  `Mod/Part RefineModel=true` (refine corrupts tangent OpenSCAD geometry).
* `test_import_circle_not_leaked` — consumed 2D circles must not remain as
  extra document roots.
* `test_import_union_2d_unified` / `test_import_offset_fillet_closing` /
  `test_import_offset_chain_circle_hole` — 2D booleans are unified into
  region faces (OpenSCAD semantics) so `offset()` closing generates fillets
  correctly and offset-of-offset chains do not crash OCC.
* `test_import_offset_childless` / `test_import_offset_background_only_child` /
  `test_import_offset_3d_child_ignored` — `offset()` edge cases that render
  empty in OpenSCAD (childless form, all-children-dropped, 2D-only
  operation over a 3D child) import as empty instead of crashing.

When fixing an importer bug, add the regression here and red/green-verify
it: stash the fix, confirm the test fails, restore, confirm green (the
workflow is described in `src/Mod/OpenSCAD/csg_isolation/README.md`).
