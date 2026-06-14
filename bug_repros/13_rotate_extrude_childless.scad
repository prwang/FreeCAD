// SYMPTOM: import aborted during parse with KeyError: 'file' (or, for a file
//   without a dot like file = "45", ValueError: not enough values to unpack).
//   A childless rotate_extrude() compiles to the same SEMICOLON form that a
//   profile-importing rotate_extrude uses: rotate_extrude(angle=360, ...);
// CAUSE: p_rotate_extrude_file assumed the 'file' kwarg was always present and
//   did p[3]['file'].rsplit('.', 1).
// FIX: importCSG.py p_rotate_extrude_file -> if 'file' not in p[3]: return []
//   (revolves nothing -> empty), and pad the extension split so a dot-less file
//   no longer fails to unpack. Commit 12cbeaa3b2.
// EXPECTED (OpenSCAD): a childless rotate_extrude renders empty; a sibling cube
//   in the same union imports unaffected.
union() {
	rotate_extrude();
	cube([10, 10, 10]);
}
