// SYMPTOM: a rotate_extrude(file="...") with an unopenable file aborted the WHOLE
//   import. t3d__rotate_extrude-angle opens with
//   `rotate_extrude(file="45", ... angle=360);` and died at parse with
//   `ValueError: Unsupported file extension `, losing the file's other 4 valid
//   rotate_extrude(angle=...) statements (Category C: a hard error, no STEP).
// CAUSE: file="45" is OpenSCAD's deprecated 2D-profile DXF-import form. The
//   importer split "45" -> filen="45", ext="" and called process_import_file,
//   which raises ValueError on the empty/unsupported extension (importCSG.py
//   ~L1014). The exception propagated out of p_rotate_extrude_file and killed
//   the whole document.
// FIX: importCSG.py p_rotate_extrude_file -> wrap process_import_file in
//   try/except (ValueError, FileNotFoundError): warn and render empty, mirroring
//   import()-of-a-missing-file and the childless-rotate_extrude path right above.
//   Commit <C1-HASH>.
// EXPECTED (OpenSCAD): rotate_extrude with an unopenable file warns and renders
//   empty; it does not abort the model. Sibling geometry (here cube([3,3,3]),
//   volume 27) is unaffected.
// NOTE: the file="..." form cannot be expressed in modern .scad source (it is a
//   deprecated compiled-CSG construct); compile-and-import the matching .csg
//   `rotate_extrude(file="45", layer="", angle=360, $fn=0, $fa=15, $fs=4);` to
//   reproduce. The cube below stands in for the surviving siblings.
cube([3, 3, 3]);
