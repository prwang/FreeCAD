#!/usr/bin/env python3
"""Validate FreeCAD CSG conversions against OpenSCAD reference geometry.

For each <name>.csg:
  1. render reference mesh:   openscad -o csg_out/<name>.ref.stl <name>.csg
  2. compare with FreeCAD's   csg_out/<name>.stl  (written by csg2step.py)
     via mesh volume (divergence theorem) and bounding box.

Pure python (no FreeCAD). Writes csg_out/validation.json and prints a table.

Usage: python3 validate.py [--tests DIR] [--out DIR] [--timeout S]
                           [--mem-gb GB] [--vol-tol PCT] [--bbox-tol MM]
                           [--refine-fn N] [names...]

Reference renders run under an address-space cap (default 4 GB, Linux/macOS):
CGAL renders (e.g. minkowski) can otherwise OOM the whole machine. A case
whose reference needs more is discarded (NO-REF).

Faceting vs. real bug
---------------------
OpenSCAD approximates curved primitives with `$fn` inscribed facets; FreeCAD
builds the exact smooth solid. The volume gap that produces is geometry, not a
defect, and below $fn~50 it dwarfs the 2 % tolerance. Two knobs separate it
from real bugs:

  --refine-fn N  (authoritative)  re-render the reference with every baked
                 `$fn` forced to N (default 128 -> deficit < 0.1 %). A mismatch
                 that collapses was faceting; one that survives is a real bug.
  analytic envelope (secondary)   without --refine-fn, the per-case tolerance is
                 widened to the known deficit delta(n_min) for the file's
                 coarsest curved primitive, so a plain run already suppresses
                 most faceting false positives. A sanity aid, not the authority.
"""

import argparse
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys

try:
    import resource
except ImportError:  # Windows: no rlimits; renders run uncapped
    resource = None

HERE = os.path.dirname(os.path.abspath(__file__))


def mem_limiter(mem_gb):
    """Return a subprocess preexec_fn capping the child's address space, or
    None where rlimits are unavailable (Windows)."""
    if not resource or not mem_gb:
        return None
    limit = int(mem_gb * (1 << 30))

    def _limit():
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    return _limit


def find_openscad():
    """$CSG2STEP_OPENSCAD, then $PATH, then the standard Windows install
    locations (mirrors OpenSCADUtils.searchforopenscadexe, which cannot be
    imported here because this script runs without FreeCAD)."""
    env = os.environ.get("CSG2STEP_OPENSCAD")
    if env:
        return env
    cand = shutil.which("openscad")
    if cand:
        return cand
    if sys.platform == "win32":
        for base in (os.environ.get("ProgramW6432"),
                     os.environ.get("Programfiles(x86)"),
                     os.environ.get("ProgramFiles")):
            if base:
                p = os.path.join(base, "OpenSCAD", "openscad.exe")
                if os.path.isfile(p):
                    return p
    return None


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


# $fn is baked into every curved primitive of a compiled .csg as an explicit
# arg, e.g. `sphere($fn = 0, $fa = 12, $fs = 2, r = 5);`. A global `$fn=N;`
# prepended to the file would NOT override these, so we rewrite them in place.
FN_RE = re.compile(r"(\$fn\s*=\s*)([0-9.eE+-]+)")


def delta2(n):
    """Area deficit fraction of an inscribed regular n-gon vs its circle:
    delta2(n) = 1 - sin(2pi/n)/(2pi/n) ~= 2pi^2/(3 n^2). Exact for 2D
    circles/cylinder cross-sections."""
    n = max(n, 3.0)
    a = 2.0 * math.pi / n
    return 1.0 - math.sin(a) / a


def delta3(n):
    """Volume deficit fraction of OpenSCAD's $fn-faceted sphere vs the exact
    sphere. Empirical: delta3(n) ~= 16.4/n^2 (OpenSCAD's UV sphere is coarser
    than the simple ring model; the constant is asymptotic)."""
    n = max(n, 3.0)
    return 16.4 / (n * n)


def effective_n(content):
    """The coarsest curved primitive in the file, as an effective facet count,
    or None if the file has no curved primitives. $fn>0 wins (clamped to 3);
    $fn==0 means OpenSCAD derives n from $fa/$fs -- approximated by the
    $fa=12 default of ~30 fragments (this is why --refine-fn, not the
    envelope, is authoritative for $fn=0 cases)."""
    ns = []
    for m in FN_RE.finditer(content):
        v = float(m.group(2))
        ns.append(30.0 if v == 0 else max(v, 3.0))
    return min(ns) if ns else None


def facet_deficit(content, twoD):
    """(deficit fraction delta, effective n) for the file's coarsest curved
    primitive, or (None, None) if it has none. Conservative upper bound: treats
    the whole volume/extent as curved."""
    n = effective_n(content)
    if n is None:
        return None, None
    return (delta2(n) if twoD else delta3(n)), n


def facet_tolerances(d, n, vol_tol, bbox_tol):
    """Widen the volume and bbox tolerances to absorb pure faceting at the
    given deficit. Volume: OpenSCAD's reference is the *inscribed* (smaller)
    solid, so the measured error |Vfc-Vref|/Vref equals delta/(1-delta), not
    delta. Bbox: inscription pulls each curved extent inward by a factor
    (1-cos(pi/n)); applied to the reference's largest extent as an upper
    bound. Returns (vol_tol_pct, bbox_tol_mm, ref_extent_factor)."""
    vol = max(vol_tol, 100.0 * d / (1.0 - d)) if d < 1.0 else float("inf")
    bbox_frac = 1.0 - math.cos(math.pi / max(n, 3.0))
    return vol, bbox_tol, bbox_frac


def prepare_ref_csg(csg, out, name, twoD, refine_fn):
    """Build the .csg openscad should render as the reference, applying (a) the
    $fn refinement and (b) the 1 mm extrusion for 2D cases (which openscad
    cannot STL-render directly; csg2step extrudes the FreeCAD result the same
    way). Returns (path_to_render, ref_stl_tag). Renders the original file
    in place when neither transform applies."""
    content = open(csg).read()
    tag = ""
    if refine_fn:
        content = FN_RE.sub(lambda m: m.group(1) + str(refine_fn), content)
        tag += ".fn%d" % refine_fn
    if twoD:
        content = "linear_extrude(height = 1) {\n" + content + "\n}\n"
        tag += ".2dref"
    if not tag:
        return csg, ""
    path = os.path.join(out, name + tag + ".csg")
    if not (os.path.isfile(path) and open(path).read() == content):
        with open(path, "w") as f:
            f.write(content)
    return path, tag


def reftag(refine_fn):
    """STL cache suffix; keeps refined and un-refined renders distinct so a
    --refine-fn run never reuses a stale plain reference (or vice versa)."""
    return ".fn%d" % refine_fn if refine_fn else ""


def render_one(args, csg, name, twoD, refine_fn):
    """Prepare the reference .csg (optional $fn refine + 2D wrap) and render it
    to <name>[.fnN].ref.stl. Returns an error string, or None on success."""
    ref_csg, _ = prepare_ref_csg(csg, args.out, name, twoD, refine_fn)
    ref = os.path.join(args.out, name + reftag(refine_fn) + ".ref.stl")
    try:
        return render_reference(args.openscad, ref_csg, ref, args.timeout,
                                args.mem_gb)
    except subprocess.TimeoutExpired:
        return "openscad timeout"


def render_reference(openscad, csg, ref_stl, timeout, mem_gb):
    if os.path.isfile(ref_stl) and os.path.getmtime(ref_stl) > os.path.getmtime(csg):
        return None  # cached
    p = subprocess.run([openscad, "-o", ref_stl, csg],
                       capture_output=True, text=True, timeout=timeout,
                       preexec_fn=mem_limiter(mem_gb))
    if p.returncode != 0 or not os.path.isfile(ref_stl):
        err = (p.stderr or "").strip()
        if p.returncode and p.returncode < 0 or "bad_alloc" in err \
                or "Cannot allocate" in err:
            return "openscad killed (likely > %sGB memory cap), discarded" % mem_gb
        return "openscad failed: " + err[-200:]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", default=os.path.join(HERE, "corpus"),
                    help="directory of .csg cases (default: bundled corpus)")
    ap.add_argument("--out", default=os.path.join(os.getcwd(), "csg_out"))
    ap.add_argument("--openscad", default=None,
                    help="openscad binary for reference renders (default: auto-detect)")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--mem-gb", type=float, default=4.0,
                    help="reference-render address-space cap in GB; 0 = uncapped "
                         "(default 4: hungrier cases are discarded)")
    ap.add_argument("--vol-tol", type=float, default=2.0,
                    help="max |dV|/Vref in percent (floor; widened per case by "
                         "the faceting envelope unless --refine-fn is given)")
    ap.add_argument("--bbox-tol", type=float, default=0.1,
                    help="max bbox component delta in mm")
    ap.add_argument("--refine-fn", type=int, default=0, metavar="N",
                    help="re-render the reference with every baked $fn forced "
                         "to N (e.g. 128) so faceting deficit is negligible; "
                         "the authoritative faceting-vs-bug classifier. "
                         "0 = off (use the analytic envelope instead)")
    ap.add_argument("names", nargs="*")
    args = ap.parse_args()

    if not args.openscad:
        args.openscad = find_openscad()
        if not args.openscad:
            sys.exit("openscad not found: pass --openscad or set $CSG2STEP_OPENSCAD")

    os.makedirs(args.out, exist_ok=True)
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
        twoD = bool(summary.get(name, {}).get("twoD"))
        d, fn_min = facet_deficit(open(csg).read(), twoD)
        fc = os.path.join(args.out, name + ".stl")
        rec = {"name": name}
        if fn_min is not None:
            rec["fn_min"] = round(fn_min, 3)

        # Render the reference. With --refine-fn we force $fn high so the
        # reference is effectively smooth; if that render dies (heavy meshes
        # OOM the 4 GB cap), fall back to the un-refined render + envelope so
        # the case is still classified rather than lost as NO-REF.
        refined = bool(args.refine_fn)
        err = render_one(args, csg, name, twoD, args.refine_fn if refined else 0)
        if err and refined:
            refined = False
            err = render_one(args, csg, name, twoD, 0)
            rec["refine_failed"] = True
        ref = os.path.join(args.out, name + reftag(args.refine_fn if refined else 0)
                           + ".ref.stl")

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
            bbox_delta = max(abs(a - b) for pa, pb in zip(bref, bfc)
                             for a, b in zip(pa, pb))
            rec["bbox_max_delta"] = round(bbox_delta, 3)
            # A smooth (refined) reference gets the tight floor; otherwise widen
            # both tolerances to absorb the analytic faceting deficit.
            if refined:
                rec["refined_fn"] = args.refine_fn
                vol_tol, bbox_tol = args.vol_tol, args.bbox_tol
            elif d is not None:
                vol_tol, bbox_tol, bfrac = facet_tolerances(
                    d, fn_min, args.vol_tol, args.bbox_tol)
                extent = max(hi - lo for lo, hi in zip(bref[0], bref[1]))
                bbox_tol = max(bbox_tol, bfrac * extent)
            else:
                vol_tol, bbox_tol = args.vol_tol, args.bbox_tol
            rec["vol_tol_used"] = round(vol_tol, 3)
            rec["bbox_tol_used"] = round(bbox_tol, 3)
            bad_v = rec["vol_err_pct"] is None or rec["vol_err_pct"] > vol_tol
            bad_b = rec["bbox_max_delta"] > bbox_tol
            rec["status"] = "MATCH" if not (bad_v or bad_b) else "MISMATCH"
        print("[%2d/%d] %-32s %-13s vol_err=%s%% (tol %s) bbox_d=%s%s %s" % (
            i, len(names), name, rec["status"],
            rec.get("vol_err_pct", "-"), rec.get("vol_tol_used", "-"),
            rec.get("bbox_max_delta", "-"),
            " refine-OOM" if rec.get("refine_failed") else "",
            (rec.get("error") or "")[:50]), flush=True)
        records.append(rec)

    with open(os.path.join(args.out, "validation.json"), "w") as f:
        json.dump(records, f, indent=1)

    n = lambda s: sum(1 for r in records if r["status"] == s)
    print("\n%d MATCH, %d MISMATCH, %d NO-CONVERSION, %d NO-REF  (validation.json)"
          % (n("MATCH"), n("MISMATCH"), n("NO-CONVERSION"), n("NO-REF")))


if __name__ == "__main__":
    main()
