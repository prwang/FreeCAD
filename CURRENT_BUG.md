# CURRENT BUG — (none active)

No bug under investigation. Last resolved (this session, in order): A4 resize()
orphan-source leak (`b8a90c6d93`), A5 linear_extrude twist + point-collapse null
(`8e36697899`), A6 resize() negative newsize (`561edf6ebe`). Each red/green with a
minimized analytic unit test + a `bug_repros/` .scad. Gates after A6: unit suite
**57/57 OK**; dev corpus **35/35 convert + 35 MATCH**.

Now running the full 204-case regression sweep (A4+A5+A6 combined) to confirm 0
global regressions vs the postfix-sweep baseline (`e120905e12`).

When the next non-trivial bug appears, overwrite this file with the mandatory
template (per CLAUDE.md — do NOT edit importer code before a hypothesis is
accepted by conclusive evidence that also rejects the competitors):

## Observation
- exact symptom, file, reproduction, stage/error.

## Hypotheses (each independently testable)
- H1: …

## Evidence log
- probe → what it showed.

## Verdict
- which hypotheses ACCEPTED/REJECTED and why.
