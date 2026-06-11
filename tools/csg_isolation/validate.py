#!/usr/bin/env python3
"""Validate FreeCAD CSG conversions against OpenSCAD reference geometry.

For each <name>.csg:
  1. render reference mesh:   openscad -o csg_out/<name>.ref.stl <name>.csg
  2. compare with FreeCAD's   csg_out/<name>.stl  (written by csg2step.py)
     via mesh volume (divergence theorem) and bounding box.

Pure python (no FreeCAD). Writes csg_out/validation.json and prints a table.

Usage: python3 validate.py [--tests DIR] [--out DIR] [--timeout S]
                           [--vol-tol PCT] [--bbox-tol MM] [names...]
"""

import argparse
import json
import os
import struct
import subprocess
import sys


def read_stl(path):
    """Return (volume, bbox) of an STL file. bbox = (min xyz, max xyz)."""
    with open(path, "rb") as f:
        head = f.read(5)
        f.seek(0)
        if head == b"solid":
            # could still be binary (some exporters write 'solid' in header);
            # try ascii, fall back to binary
            try:
                return _read_stl_ascii(f)
            except (UnicodeDecodeError, ValueError):
                f.seek(0)
                return _read_stl_bin(f)
        return _read_stl_bin(f)


def _accumulate(tri, acc):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = tri
    # signed volume of tetrahedron (origin, a, b, c)
    acc[0] += (ax * (by * cz - bz * cy)
               - ay * (bx * cz - bz * cx)
               + az * (bx * cy - by * cx)) / 6.0
    for p in tri:
        for i in range(3):
            acc[1][i] = min(acc[1][i], p[i])
            acc[2][i] = max(acc[2][i], p[i])


def _read_stl_bin(f):
    f.seek(80)
    (n,) = struct.unpack("<I", f.read(4))
    acc = [0.0, [1e30] * 3, [-1e30] * 3]
    rec = struct.Struct("<12fH")
    data = f.read(n * 50)
    if len(data) < n * 50:
        raise ValueError("truncated binary STL")
    for i in range(n):
        v = rec.unpack_from(data, i * 50)
        _accumulate((v[3:6], v[6:9], v[9:12]), acc)
    return abs(acc[0]), (acc[1], acc[2])


def _read_stl_ascii(f):
    acc = [0.0, [1e30] * 3, [-1e30] * 3]
    tri = []
    seen = False
    for line in f.read().decode("ascii").splitlines():
        parts = line.split()
        if parts[:1] == ["vertex"]:
            tri.append(tuple(float(x) for x in parts[1:4]))
            if len(tri) == 3:
                _accumulate(tri, acc)
                tri = []
                seen = True
    if not seen:
        raise ValueError("no facets in ascii STL")
    return abs(acc[0]), (acc[1], acc[2])


def wrap_2d(csg, out, name):
    """2D models cannot be STL-rendered by openscad; both sides compare 1mm
    extrusions instead (csg2step extrudes the FreeCAD result the same way)."""
    with open(csg) as f:
        content = f.read()
    wrapped = "linear_extrude(height = 1) {\n" + content + "\n}\n"
    path = os.path.join(out, name + ".2dref.csg")
    if not (os.path.isfile(path) and open(path).read() == wrapped):
        with open(path, "w") as f:
            f.write(wrapped)
    return path


def render_reference(csg, ref_stl, timeout):
    if os.path.isfile(ref_stl) and os.path.getmtime(ref_stl) > os.path.getmtime(csg):
        return None  # cached
    p = subprocess.run(["openscad", "-o", ref_stl, csg],
                       capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0 or not os.path.isfile(ref_stl):
        return "openscad failed: " + (p.stderr or "").strip()[-200:]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", default="/work/FreeCAD/csg_tests")
    ap.add_argument("--out", default="/work/FreeCAD/csg_out")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--vol-tol", type=float, default=2.0,
                    help="max |dV|/Vref in percent")
    ap.add_argument("--bbox-tol", type=float, default=0.1,
                    help="max bbox component delta in mm")
    ap.add_argument("names", nargs="*")
    args = ap.parse_args()

    names = args.names or sorted(
        os.path.splitext(f)[0] for f in os.listdir(args.tests)
        if f.endswith(".csg"))

    summary = {}
    spath = os.path.join(args.out, "summary.json")
    if os.path.isfile(spath):
        try:
            with open(spath) as f:
                summary = {r["name"]: (r.get("result") or {})
                           for r in json.load(f)}
        except Exception:
            pass

    records = []
    for i, name in enumerate(names, 1):
        csg = os.path.join(args.tests, name + ".csg")
        if summary.get(name, {}).get("twoD"):
            csg = wrap_2d(csg, args.out, name)
        ref = os.path.join(args.out, name + ".ref.stl")
        fc = os.path.join(args.out, name + ".stl")
        rec = {"name": name}
        try:
            err = render_reference(csg, ref, args.timeout)
        except subprocess.TimeoutExpired:
            err = "openscad timeout"
        if err:
            rec["status"] = "NO-REF"
            rec["error"] = err
        elif not os.path.isfile(fc):
            rec["status"] = "NO-CONVERSION"
            rec["error"] = "freecad stl missing (conversion failed)"
        else:
            vref, bref = read_stl(ref)
            vfc, bfc = read_stl(fc)
            rec["vol_ref"], rec["vol_fc"] = round(vref, 3), round(vfc, 3)
            rec["vol_err_pct"] = round(100.0 * abs(vfc - vref) / vref, 3) if vref else None
            rec["bbox_max_delta"] = round(max(
                abs(a - b) for pa, pb in zip(bref, bfc)
                for a, b in zip(pa, pb)), 3)
            bad_v = rec["vol_err_pct"] is None or rec["vol_err_pct"] > args.vol_tol
            bad_b = rec["bbox_max_delta"] > args.bbox_tol
            rec["status"] = "MATCH" if not (bad_v or bad_b) else "MISMATCH"
        print("[%2d/%d] %-32s %-13s vol_err=%s%% bbox_d=%s %s" % (
            i, len(names), name, rec["status"],
            rec.get("vol_err_pct", "-"), rec.get("bbox_max_delta", "-"),
            (rec.get("error") or "")[:60]), flush=True)
        records.append(rec)

    with open(os.path.join(args.out, "validation.json"), "w") as f:
        json.dump(records, f, indent=1)

    n = lambda s: sum(1 for r in records if r["status"] == s)
    print("\n%d MATCH, %d MISMATCH, %d NO-CONVERSION, %d NO-REF  (validation.json)"
          % (n("MATCH"), n("MISMATCH"), n("NO-CONVERSION"), n("NO-REF")))


if __name__ == "__main__":
    main()
