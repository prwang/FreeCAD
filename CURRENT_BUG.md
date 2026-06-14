# CURRENT BUG — (none active)

No bug under investigation. Last resolved:
- `inf`/`nan` literals derailing the parser → committed `61d6b153f3`. Lexer now
  lexes inf/nan as NUMBER; primitives guard non-finite $fn (→ smooth) and
  non-finite dimension/vertex (→ empty), matching OpenSCAD's undef semantics.
  primitive-inf-tests crash/empty → 2 finite solids (π, 4π/3); 51/51 unit;
  dev corpus 34 MATCH / 1 NO-REF (no regression).
- Before that: routing_tiles all-null → committed `024eff9443`.

When the next non-trivial bug appears, overwrite this file with the mandatory
template (per CLAUDE.md — do NOT edit importer code before a hypothesis is
accepted by conclusive evidence that also rejects the competitors):

## Observation
- exact symptom, file, reproduction, stage/error.

## Hypotheses (each independently testable)
- H1: …
- H2: …

## Evidence log
- probe → what it showed.

## Verdict
- which hypotheses ACCEPTED/REJECTED and why.
