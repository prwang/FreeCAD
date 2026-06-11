"""Brace-aware subtree splitter for .csg minimization.

Usage: python3 minimize.py <file.csg> <out_dir> [path]
Splits the node at `path` (e.g. "0.2" = first child's third child) into one
file per child subtree, preserving no wrapping (children become top-level).
Also writes <name>.keep<i>.csg variants = original tree with only child i
of the target node kept (preserves the wrapping context).
"""

import sys


def parse_children(text, start):
    """Return list of (label_start, body_open, body_close) for the children
    of the block whose '{' is at index start."""
    children = []
    i = start + 1
    depth = 0
    label_start = None
    while i < len(text):
        c = text[i]
        if label_start is None and not c.isspace() and c != '}':
            label_start = i
        if c == '{':
            depth += 1
            if depth == 1:
                open_idx = i
        elif c == '}':
            if depth == 0:
                return children
            depth -= 1
            if depth == 0:
                children.append((label_start, open_idx, i))
                label_start = None
        elif c == ';' and depth == 0:
            children.append((label_start, None, i))
            label_start = None
        i += 1
    return children


def main():
    src, outdir = sys.argv[1], sys.argv[2]
    path = [int(x) for x in sys.argv[3].split('.')] if len(sys.argv) > 3 else []
    text = open(src).read()
    # virtual root block spanning the whole file
    node_open = -1
    for step in path:
        kids = parse_children(text, node_open)
        node_open = kids[step][1]
    kids = parse_children(text, node_open)
    import os
    base = os.path.splitext(os.path.basename(src))[0]
    for n, (ls, op, cl) in enumerate(kids):
        sub = text[ls:cl + 1]
        with open(f"{outdir}/{base}.sub{n}.csg", "w") as f:
            f.write(sub + "\n")
        # keep<i>: original file with the target node reduced to child i only
        kept = text[:kids[0][0]] + sub + "\n" + text[kids[-1][2] + 1:] \
            if node_open >= 0 else sub + "\n"
        with open(f"{outdir}/{base}.keep{n}.csg", "w") as f:
            f.write(kept)
        print(f"sub{n}: {len(sub)} chars, head: {sub[:60].strip()!r}")


main()
