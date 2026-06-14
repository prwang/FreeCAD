# CURRENT BUG — (none active)

No bug under investigation. Resolved this session (newest first):
- A8 `8e36697899`→`e3b64af870` linear_extrude twist + LINE collapse (one zero
  scale) → null for some angles (e.g. twist180 scale=[0,1]). Single-wire now
  lofts a valid solid via `_twisted_taper_solid`; holed/self-intersecting
  twisted taper-to-line left empty (genuine UNKNOWN), never an invalid compound.
- A7 `07d36bceee` resize() auto-scale matched to OpenSCAD 2021.01 exactly
  (autoscale = max of explicit per-axis factors). The whole resize cluster now
  MATCHes: resize-tests 36.9 %→0.24 %, resize-2d 14.8 %→0.0 %.
- A6 `561edf6ebe` resize() negative newsize → axis unchanged (was a mirror).
- A5 `8e36697899` linear_extrude twist + POINT collapse (scale=[0,0]) → null;
  point apex is twist-invariant → pyramid base·h/3.
- A4 `b8a90c6d93` resize() orphan-source leak.
- Comparator: validate.py `--refine-fn` now refines twist `slices` too, so a
  smooth-correct twist (FreeCAD = the exact slices→∞ limit) no longer reads as a
  faceting mismatch (`6675ba2ecc`).

Gates after A8: unit suite 59/59 OK; dev corpus 35/35 convert + 35 MATCH.

Still genuinely hard / postponed: holed twisted taper-to-line (self-intersecting,
no clean OCC solid); ex__linear_extrude bbox offset (non-faceting, separate);
linear_extrude_invisible-tests (34.7 %, separate degenerate cluster).

When the next non-trivial bug appears, overwrite this file with the mandatory
template (Observation / Hypotheses / Evidence log / Verdict) per CLAUDE.md.
