#!/usr/bin/env python3
"""Run csg2step.py over a directory of .csg files, one FreeCADCmd process per
file (crash/hang isolation), and print a summary table.

Usage: python3 run_all.py [--freecadcmd PATH] [--tests DIR] [--out DIR]
                          [--timeout SECONDS] [files...]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MARKER = re.compile(r"CSG2STEP_RESULT_BEGIN\n(.*?)\nCSG2STEP_RESULT_END", re.S)


def run_one(freecadcmd, csg, outdir, timeout):
    name = os.path.splitext(os.path.basename(csg))[0]
    step = os.path.join(outdir, name + ".step")
    log = os.path.join(outdir, name + ".log")
    cmd = [freecadcmd, os.path.join(HERE, "csg2step.py")]
    env = dict(os.environ, CSG2STEP_IN=csg, CSG2STEP_OUT=step)
    t0 = time.time()
    rec = {"name": name, "csg": csg, "step": step}
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           env=env)
        out = p.stdout + "\n--- stderr ---\n" + p.stderr
        rec["exit"] = p.returncode
        m = MARKER.search(p.stdout)
        if m:
            rec["result"] = json.loads(m.group(1))
        elif p.returncode != 0:
            rec["result"] = {"stage": "crash", "ok": False,
                             "error": "exit code %d, no result marker" % p.returncode}
        else:
            rec["result"] = {"stage": "unknown", "ok": False,
                             "error": "no result marker in output"}
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") + "\n--- stderr ---\n" + (e.stderr or "")
        rec["exit"] = None
        rec["result"] = {"stage": "timeout", "ok": False,
                         "error": "timed out after %ds" % timeout}
    rec["wall"] = round(time.time() - t0, 1)
    with open(log, "w") as f:
        f.write(out)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freecadcmd", default=os.environ.get(
        "FREECADCMD", "/work/FreeCAD/build/headless/bin/FreeCADCmd"))
    ap.add_argument("--tests", default="/work/FreeCAD/csg_tests")
    ap.add_argument("--out", default="/work/FreeCAD/csg_out")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("files", nargs="*")
    args = ap.parse_args()

    files = args.files or sorted(
        os.path.join(args.tests, f) for f in os.listdir(args.tests)
        if f.endswith(".csg"))
    os.makedirs(args.out, exist_ok=True)

    records = []
    for i, csg in enumerate(files, 1):
        rec = run_one(args.freecadcmd, csg, args.out, args.timeout)
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
