#!/usr/bin/env python3
"""Run csg2step.py over a directory of .csg files, one FreeCADCmd process per
file (crash/hang isolation), and print a summary table.

Usage: python3 run_all.py [--freecadcmd PATH] [--tests DIR] [--out DIR]
                          [--timeout SECONDS] [--mem-gb GB] [files...]

Each conversion runs under an address-space cap (default 4 GB, Linux/macOS);
a case that needs more dies alone with stage=oom instead of taking the
machine down, and is treated as discarded.

Defaults are deployment-friendly: FreeCADCmd is located relative to this
script (it ships at <prefix>/Mod/OpenSCAD/csg_isolation, so the binary is at
<prefix>/bin), the test set defaults to the bundled minimal corpus/, and
output goes to ./csg_out in the current directory.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

try:
    import resource
except ImportError:  # Windows: no rlimits; cases run uncapped
    resource = None

HERE = os.path.dirname(os.path.abspath(__file__))
MARKER = re.compile(r"CSG2STEP_RESULT_BEGIN\n(.*?)\nCSG2STEP_RESULT_END", re.S)


def mem_limiter(mem_gb):
    """Return a subprocess preexec_fn capping the child's address space, or
    None where rlimits are unavailable (Windows)."""
    if not resource or not mem_gb:
        return None
    limit = int(mem_gb * (1 << 30))

    def _limit():
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    return _limit


def find_freecadcmd():
    """Locate FreeCADCmd: $FREECADCMD, then <prefix>/bin next to this script
    (the layout of both the build tree and every installed package), then
    $PATH (covers the deb /usr/bin symlink and the conda 'freecadcmd')."""
    env = os.environ.get("FREECADCMD")
    if env:
        return env
    prefix = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    exe = ".exe" if sys.platform == "win32" else ""
    for name in ("FreeCADCmd" + exe, "freecadcmd" + exe):
        cand = os.path.join(prefix, "bin", name)
        if os.path.isfile(cand):
            return cand
    for name in ("FreeCADCmd", "freecadcmd"):
        cand = shutil.which(name)
        if cand:
            return cand
    return None


OOM_HINT = re.compile(r"bad_alloc|MemoryError|Cannot allocate|out of memory", re.I)


def run_one(freecadcmd, csg, outdir, timeout, mem_gb):
    name = os.path.splitext(os.path.basename(csg))[0]
    step = os.path.join(outdir, name + ".step")
    log = os.path.join(outdir, name + ".log")
    cmd = [freecadcmd, os.path.join(HERE, "csg2step.py")]
    env = dict(os.environ, CSG2STEP_IN=csg, CSG2STEP_OUT=step)
    t0 = time.time()
    rec = {"name": name, "csg": csg, "step": step}
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           env=env, preexec_fn=mem_limiter(mem_gb))
        out = p.stdout + "\n--- stderr ---\n" + p.stderr
        rec["exit"] = p.returncode
        m = MARKER.search(p.stdout)
        if m:
            rec["result"] = json.loads(m.group(1))
        elif p.returncode != 0:
            if OOM_HINT.search(out):
                rec["result"] = {"stage": "oom", "ok": False,
                                 "error": "exceeded %sGB memory cap, discarded" % mem_gb}
            else:
                rec["result"] = {"stage": "crash", "ok": False,
                                 "error": "exit code %d, no result marker" % p.returncode}
        else:
            rec["result"] = {"stage": "unknown", "ok": False,
                             "error": "no result marker in output"}
    except subprocess.TimeoutExpired as e:
        # TimeoutExpired carries bytes even when run() uses text=True
        def _text(x):
            return x.decode(errors="replace") if isinstance(x, bytes) else (x or "")
        out = _text(e.stdout) + "\n--- stderr ---\n" + _text(e.stderr)
        rec["exit"] = None
        rec["result"] = {"stage": "timeout", "ok": False,
                         "error": "timed out after %ds" % timeout}
    rec["wall"] = round(time.time() - t0, 1)
    with open(log, "w") as f:
        f.write(out)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freecadcmd", default=None,
                    help="FreeCADCmd binary (default: auto-detect)")
    ap.add_argument("--tests", default=os.path.join(HERE, "corpus"),
                    help="directory of .csg cases (default: bundled corpus)")
    ap.add_argument("--out", default=os.path.join(os.getcwd(), "csg_out"))
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--mem-gb", type=float, default=4.0,
                    help="per-case address-space cap in GB; 0 = uncapped "
                         "(default 4: hungrier cases are discarded)")
    ap.add_argument("files", nargs="*")
    args = ap.parse_args()

    if not args.freecadcmd:
        args.freecadcmd = find_freecadcmd()
        if not args.freecadcmd:
            sys.exit("FreeCADCmd not found: pass --freecadcmd or set $FREECADCMD")

    files = args.files or sorted(
        os.path.join(args.tests, f) for f in os.listdir(args.tests)
        if f.endswith(".csg"))
    os.makedirs(args.out, exist_ok=True)

    records = []
    for i, csg in enumerate(files, 1):
        rec = run_one(args.freecadcmd, csg, args.out, args.timeout, args.mem_gb)
        r = rec["result"]
        status = "OK" if r.get("ok") is True else (
            "SUSPECT" if r.get("ok") == "suspect" else "FAIL@" + str(r.get("stage")))
        print("[%2d/%d] %-32s %-18s %5.1fs  %s" % (
            i, len(files), rec["name"], status, rec["wall"],
            (r.get("error") or "")[:90]), flush=True)
        records.append(rec)

    with open(os.path.join(args.out, "summary.json"), "w") as f:
        json.dump(records, f, indent=1)

    ok = sum(1 for r in records if r["result"].get("ok") is True)
    sus = sum(1 for r in records if r["result"].get("ok") == "suspect")
    print("\n%d/%d ok, %d suspect, %d failed   (details: %s/summary.json)" % (
        ok, len(records), sus, len(records) - ok - sus, args.out))


if __name__ == "__main__":
    main()
