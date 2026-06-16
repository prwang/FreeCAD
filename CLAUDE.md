# CLAUDE.md — OpenSCAD CSG→STEP importer hardening (dev workflow, NOT for the PR)

This file is dev-workflow guidance for work on branch `fix-csg`. It is NOT meant
for the eventual upstream PR, but it IS version-controlled on our fork (see
below) so we can refer back to it while fixing bugs.

## Versioning the self-docs (our fork) vs the upstream PR
Current priority: **get the code working.** This is a big effort; a dedicated
later PR-writing stage will produce the upstream-facing docs/tests and strip the
dev scaffolding, *guided by* these self-docs and repros. So during development we
**track** our own working docs on `fix-csg` (commit them, so a later fix that
regresses an earlier one has a place to be checked against):
- TRACK: `CLAUDE.md`, `CURRENT_BUG.md`, `BACKLOG.md` (the in-tree working plan /
  planning history; moved in-tree 2026-06-16 so the plan is version-controlled),
  `bug_repros/` (the `.scad` + `README.md`; NOT the regenerable compiled
  `bug_repros/out/`).
- STAY UNTRACKED (large / regenerable / not ours to ship): `csg_external/` (the
  204-case corpus), `csg_out/`, `bug_repros/out/`, `csg_tests.tar`.

We are NOT writing the PR-facing public docs yet — defer the upstream-shaped
`OpenSCADTest/test_information.md` regression index and the
`csg_tests/external/RESULTS.md` reclassification write-up to the PR-writing
stage. During the bugfix we document for ourselves: `CURRENT_BUG.md` (per the
rules below) and a minimized `.scad` repro per fixed defect (rule 6).

## What we are fixing
FreeCAD's OpenSCAD `.csg`→STEP importer (`src/Mod/OpenSCAD/importCSG.py`, a pure
PLY lex/yacc parser whose `p_*_action` rules build FreeCAD document objects).
Goal: make conversion stable and geometrically correct on real-world `.csg`
well beyond the bundled tests. Driven by a 204-case external corpus (untracked,
under `csg_external/`; discovery kit in `csg_tests/external/`). The PR ships
minimal hand-written regression tests, NOT the corpus.

Standing constraints (user):
- Do NOT upstream the `cMake/.../SetupQt.cmake` headless-build fixes (on hold).
- 3D `offset()` is not the focus.
- When a file's failure is genuinely complicated / has no well-defined target,
  honestly mark it UNKNOWN/postponed rather than forcing a questionable fix.

## Triage / priority rules
- **Priority A:** crashes and wrong geometry in *simple constructs*, and bugs
  that are *easy to validate analytically*. Fix these.
- **Priority C (UNKNOWN/postpone):** any case whose failure is a **timeout or
  resource-limit (OOM) exceed** goes here — **new-corpus cases only**. A case
  that was *past-known-good and regressed* by our recent fixes is NOT Priority C
  — that is a regression and must be fixed (or the offending change reverted).
- A **null-dereference / null-shape-propagation** bug is interesting and
  tractable — prefer fixing it over deferring.
- Faceting (OpenSCAD inscribes `$fn` facets; FreeCAD builds the exact smooth
  solid) is geometry, NOT a bug. Use `validate.py --refine-fn 128` (authoritative)
  or its analytic envelope to classify; never "fix" faceting in the importer.

## Debugging rules (hard requirements)
1. **CURRENT_BUG.md is mandatory for any non-trivial bug.** Before editing
   importer code, create/maintain `/work/FreeCAD/CURRENT_BUG.md` with:
   - **Observation** — exact symptom, file, reproduction, stage/error.
   - **Hypotheses** — every plausible cause, each independently testable.
   - **Evidence log** — what each probe showed.
   - **Verdict** — which hypotheses are ACCEPTED/REJECTED and why.
   **Do not change importer code until one hypothesis is accepted by
   conclusive evidence that also rejects the competing ones.** No edits on a
   hunch. As bugs get trickier this discipline is what keeps us correct.
2. **One minimized unit test per fixed defect, showing the exact cause.**
   Every importer fix ships with a hand-written `.csg` regression in
   `OpenSCADTest/app/test_importCSG.py` via the `utility_create_csg` inline
   helper (no openscad binary needed), asserting **analytic** geometry
   (volume / area / face / root counts). The fixture must be the *minimal*
   construct that exhibits the cause.
3. **Red → green, verified.** Confirm the test FAILS on pre-fix code and PASSES
   after. Iteration loop below.
4. **Match OpenSCAD semantics**, with the analytic expected value stated in the
   test comment and the commit message (e.g. cone = base·h/3; A∩∅=∅; A∪∅=A).
5. **No-regression gates before declaring done:** the full unit suite
   (`FreeCADCmd -t TestOpenSCADApp`) AND the 35-case dev corpus
   (`run_all.py` + `validate.py --tests csg_tests`) must stay green.
6. **One minimized `.scad` repro per fixed defect (dev docs, our own).** In
   addition to the inline unit test, write a hand-minimized
   `bug_repros/NN_slug.scad` (tracked; `NN` matches commit order, `slug` the
   defect) that hits the *exact* bug point and nothing else. It is OpenSCAD
   source (compile with `openscad -o x.csg x.scad` to feed the importer; the
   `.scad` is the human-readable record). Every repro starts with a header
   comment block:
   - **SYMPTOM** — the precise pre-fix failure on this input (exact exception /
     wrong analytic value / dropped statement), reproducible by checking out the
     parent commit.
   - **CAUSE** — the one accepted hypothesis from `CURRENT_BUG.md`.
   - **FIX** — `importCSG.py`/`tokrules.py` function (and what changed), plus the
     commit hash.
   - **EXPECTED** — the OpenSCAD semantic and analytic value (e.g. cone=base·h/3;
     A∩∅=∅; $fn=inf→default facets).
   Keep an index in `bug_repros/README.md` (one line per repro). Tracked on the
   fork for our reference; the PR-writing stage decides what (if anything) ships.

## Iteration loop (build tree gotcha)
Tests load from the BUILD tree `build/headless/Mod/OpenSCAD/`, not `src/`. The
build copies sources at build time, so `src/` is authoritative for commits but
you must sync to iterate:
```
cp src/Mod/OpenSCAD/importCSG.py            build/headless/Mod/OpenSCAD/importCSG.py
cp src/Mod/OpenSCAD/OpenSCADTest/app/test_importCSG.py \
   build/headless/Mod/OpenSCAD/OpenSCADTest/app/test_importCSG.py
build/headless/bin/FreeCADCmd -t TestOpenSCADApp 2>&1 | grep -E 'Ran [0-9]+ tests|^OK$|^FAILED'
```
- For a clean RED against committed code: `git show HEAD:.../importCSG.py >
  build/.../importCSG.py`, run, then copy `src` back for GREEN.
- `FreeCADCmd -c "..."` output does not reach stdout reliably; write probe
  results to a temp file and `cat` it.
- `validate.py` is $fn-aware: `--refine-fn 128` re-renders the reference smooth
  (authoritative faceting-vs-bug classifier); envelope is the always-on
  secondary. Full envelope baseline backed up at
  `csg_external/out/validation.envelope.json`.

## Commit discipline
- One commit per defect: importer fix + its regression test + a one-paragraph
  message stating the OpenSCAD semantic and the analytic expected value.
- Commit messages end with:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- The plan of record is in-tree at `/work/FreeCAD/BACKLOG.md` (tracked; moved
  from the old local plan file on 2026-06-16). Append planning entries there as
  work proceeds; the PR-writing stage strips/rewrites it.
