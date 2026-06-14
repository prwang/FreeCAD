#!/usr/bin/env python3
"""Fetch the external OpenSCAD corpus (see SOURCES.md) and compile it to .csg
for the csg_isolation pipeline.

Usage: python3 fetch_and_compile.py [--workdir DIR] [--openscad BIN] [--no-fetch]

Creates <workdir>/{repos,single,csg}; .scad files dropped manually into
<workdir>/single/ (e.g. Thingiverse/Printables downloads, see SOURCES.md
"one step away" section) are picked up too. Library files that compile to no
top-level geometry are skipped; per-file status lands in csg/harvest.json.

Then:
  python3 src/Mod/OpenSCAD/csg_isolation/run_all.py  --tests <workdir>/csg --out <workdir>/out
  python3 src/Mod/OpenSCAD/csg_isolation/validate.py --tests <workdir>/csg --out <workdir>/out
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys

try:
    import resource
except ImportError:
    resource = None

MEM_GB = 4  # cap per openscad compile; hungrier cases are discarded


def mem_limiter():
    if not resource:
        return None

    def _limit():
        lim = MEM_GB << 30
        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
    return _limit


GEOM = re.compile(r"\b(cube|sphere|cylinder|polyhedron|square|circle|polygon|"
                  r"linear_extrude|rotate_extrude|hull|minkowski|surface|text|import)\s*\(")

CLONES = [  # (url, branch-or-None)
    ("https://github.com/openscad/openscad.git", None),
    ("https://github.com/kennetek/gridfinity-rebuilt-openscad.git", None),
    ("https://github.com/jeffbarr/OpenSCADObjects.git", None),
    ("https://github.com/Irev-Dev/Round-Anything.git", None),
    ("https://github.com/openscad/MCAD.git", None),
    ("https://github.com/rsheldiii/KeyV2.git", None),
    ("https://github.com/dpellegr/PolyGear.git", None),
    ("https://github.com/jbebel/Ultimate-Box-Maker.git", None),
    ("https://github.com/prusa3d/Original-Prusa-i3.git", "MK3S"),
]

RAWS = [
    "https://raw.githubusercontent.com/adereth/dactyl-keyboard/master/things/dactyl-top-right.scad",
    "https://raw.githubusercontent.com/rcolyer/threads-scad/master/threads.scad",
]

# (tag, glob relative to workdir, exclude-basename-regex)
SELECT = [
    ("ex",       "repos/openscad/examples/Basics/*.scad", None),
    ("ex",       "repos/openscad/examples/Advanced/*.scad", None),
    ("ex",       "repos/openscad/examples/Parametric/*.scad", None),
    ("ex",       "repos/openscad/examples/Old/*.scad", None),
    ("t2d",      "repos/openscad/tests/data/scad/2D/features/*.scad", r"^text-"),
    ("t3d",      "repos/openscad/tests/data/scad/3D/features/*.scad",
                 r"^(import|surface|text)"),
    ("single",   "single/*.scad", None),
    ("ubox",     "repos/Ultimate-Box-Maker/files/Ultimate_Box.scad", None),
    ("prusa",    "repos/Original-Prusa-i3/Printed-Parts/SCAD/*.scad", None),
    ("gridfin",  "repos/gridfinity-rebuilt-openscad/gridfinity-*.scad", None),
    ("jbarr",    "repos/OpenSCADObjects/*.scad", None),
    ("roundany", "repos/Round-Anything/roundAnythingExamples.scad", None),
    ("roundany", "repos/Round-Anything/examples/*.scad", None),
    ("mcad",     "repos/MCAD/involute_gears.scad", None),
    ("mcad",     "repos/MCAD/boxes.scad", None),
    ("mcad",     "repos/MCAD/bearing.scad", None),
    ("keyv2",    "repos/KeyV2/keys.scad", None),
    ("keyv2",    "repos/KeyV2/examples/*.scad", None),
    ("polygear", "repos/PolyGear/examples/*.scad", None),
]


def fetch(workdir):
    repos = os.path.join(workdir, "repos")
    single = os.path.join(workdir, "single")
    os.makedirs(repos, exist_ok=True)
    os.makedirs(single, exist_ok=True)
    for url, branch in CLONES:
        dest = os.path.join(repos, os.path.basename(url)[:-len(".git")])
        if os.path.isdir(dest):
            continue
        cmd = ["git", "clone", "-q", "--depth", "1"]
        if branch:
            cmd += ["-b", branch]
        print("clone", url, flush=True)
        subprocess.run(cmd + [url, dest], check=True)
    for url in RAWS:
        dest = os.path.join(single, os.path.basename(url))
        if os.path.isfile(dest):
            continue
        print("fetch", url, flush=True)
        subprocess.run(["curl", "-sLo", dest, url], check=True)


def compile_all(workdir, openscad):
    out = os.path.join(workdir, "csg")
    os.makedirs(out, exist_ok=True)
    env = dict(os.environ, OPENSCADPATH=os.path.join(workdir, "repos"))
    records = []
    for tag, pattern, excl in SELECT:
        for scad in sorted(glob.glob(os.path.join(workdir, pattern))):
            base = os.path.basename(scad)
            if excl and re.match(excl, base):
                continue
            name = tag + "__" + os.path.splitext(base)[0].replace(" ", "_")
            csg = os.path.join(out, name + ".csg")
            rec = {"name": name, "scad": os.path.relpath(scad, workdir)}
            try:
                p = subprocess.run(
                    [openscad, "-o", csg, scad],
                    cwd=os.path.dirname(scad), env=env,
                    capture_output=True, text=True, timeout=120,
                    preexec_fn=mem_limiter())
                if p.returncode != 0 or not os.path.isfile(csg):
                    rec["status"] = "compile-error"
                    rec["error"] = (p.stderr or "").strip()[-300:]
                elif not GEOM.search(open(csg).read()):
                    rec["status"] = "empty"
                    os.remove(csg)
                else:
                    rec["status"] = "ok"
            except subprocess.TimeoutExpired:
                rec["status"] = "compile-timeout"
                if os.path.isfile(csg):
                    os.remove(csg)
            records.append(rec)
            print("%-15s %-44s %s" % (rec["status"], name,
                                      rec.get("error", "")[:60]), flush=True)
    with open(os.path.join(out, "harvest.json"), "w") as f:
        json.dump(records, f, indent=1)
    n = lambda s: sum(1 for r in records if r["status"] == s)
    print("\n%d ok, %d empty, %d compile-error, %d compile-timeout (of %d)" % (
        n("ok"), n("empty"), n("compile-error"), n("compile-timeout"),
        len(records)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=os.path.join(os.getcwd(), "csg_external"))
    ap.add_argument("--openscad", default=None)
    ap.add_argument("--no-fetch", action="store_true",
                    help="only recompile what is already in workdir")
    args = ap.parse_args()
    openscad = args.openscad or os.environ.get("CSG2STEP_OPENSCAD") \
        or shutil.which("openscad")
    if not openscad:
        sys.exit("openscad not found: pass --openscad or set $CSG2STEP_OPENSCAD")
    if not args.no_fetch:
        fetch(args.workdir)
    compile_all(args.workdir, openscad)


if __name__ == "__main__":
    main()
