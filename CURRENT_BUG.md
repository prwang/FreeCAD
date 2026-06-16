# CURRENT BUG — (none active)

No bug under investigation. Resolved this session (newest first):

**Category C — easiest 5 (2026-06-16).** Each xfail-with-reason or real output,
no regression. Gates after the batch: unit **64/64 OK**; dev corpus **35/35
convert + 34 MATCH / 0 MISMATCH / 1 NO-REF** (pre-existing `baseline_preview`
openscad-side timeout).
- C5 `1af659d485` `ex__module_recursion` — single-fuse tool operand was an
  invalid multi-wire 2D face (accumulated overlapping-rectangle unions, OCC
  "Unorientable"). `repair2DFaces` (ShapeFix on a mutable copy, holes-preserving;
  outer-wire fallback) + try/except repair-and-retry into a static Part::Feature.
  Crash gone; the model is also genuinely heavy (>540s) → honest Priority-C
  timeout. Test `test_repair_invalid_2d_face_for_fuse`; repro 30.
- C3/C4 `42bd59a2f5` `roundany__shell2d` / `roundany__polyround` — NOT importer
  bugs: both genuinely evaluate to empty (empty extrude body; `polygon(undef)`).
  Driver now classifies a clean no-geometry run as `empty` (exit 3, friendly
  message), not a hard error. Importer regression guards assert empty output.
- C2 `39eebb0263` `t2d__offset-tests` — `offset(){ square([0,0]) }` null operand
  guarded before `.Volume` → renders empty (was `RuntimeError: shape is invalid`
  aborting). Test `test_import_offset_empty_child_is_empty`; repro 28.
- C1 `65223cb91b` `t3d__rotate_extrude-angle` — deprecated `rotate_extrude(file=)`
  with an unopenable file renders empty + warns (was `ValueError: Unsupported
  file extension` aborting). Test `test_import_rotate_extrude_unopenable_file_is_empty`;
  repro 29.

**Earlier this session (A4–A8, newest first) — kept for cross-check.**
- A8 `8e36697899`→`e3b64af870` linear_extrude twist + LINE collapse.
- A7 `07d36bceee` resize() auto-scale (max explicit per-axis factor).
- A6 `561edf6ebe` resize() negative newsize → axis unchanged.
- A5 `8e36697899` linear_extrude twist + POINT collapse.
- A4 `b8a90c6d93` resize() orphan-source leak.
- Comparator `6675ba2ecc`: validate.py `--refine-fn` refines twist `slices`.

When the next non-trivial bug appears, overwrite this file with the mandatory
template (Observation / Hypotheses / Evidence log / Verdict) per CLAUDE.md.
