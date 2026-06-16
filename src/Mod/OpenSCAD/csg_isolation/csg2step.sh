#!/bin/sh
# csg2step.sh -- convert an OpenSCAD .csg to a STEP file, headless, no GUI.
#
# Usage:  csg2step.sh <input.csg> [output.step]
#         (output defaults to <input>.step next to the input)
#
# Exit codes:
#   0  converted     (STEP written; a '!' line means written but some shapes
#                     are geometrically invalid)
#   2  unsupported    (e.g. text()/imported DXF, or a missing referenced file)
#   3  empty model    (the model evaluated to no geometry; nothing to convert)
#   1  conversion error
#   64 usage error
#
# This wrapper exists because FreeCADCmd is a custom interpreter that treats
# positional arguments as documents to open, so paths must be passed to the
# driver (csg2step.py) through the environment, not argv. FreeCADCmd is located
# via $FREECADCMD, then <prefix>/bin next to this script (the install layout is
# <prefix>/Mod/OpenSCAD/csg_isolation), then $PATH.
set -eu

case "${1:-}" in
  -h|--help)
    echo "usage: csg2step.sh <input.csg> [output.step]"
    exit 0 ;;
  "")
    echo "usage: csg2step.sh <input.csg> [output.step]" >&2
    exit 64 ;;
esac

in=$1
case "$in" in
  *.csg) ;;
  *) echo "csg2step.sh: input must be a .csg file: $in" >&2; exit 64 ;;
esac
if [ ! -f "$in" ]; then
  echo "csg2step.sh: no such file: $in" >&2
  exit 64
fi
out=${2:-"${in%.csg}.step"}

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

find_freecadcmd() {
  if [ -n "${FREECADCMD:-}" ]; then
    printf '%s\n' "$FREECADCMD"; return 0
  fi
  prefix=$(CDPATH= cd -- "$here/../../.." && pwd)   # csg_isolation/OpenSCAD/Mod/<prefix>
  for c in "$prefix/bin/FreeCADCmd" "$prefix/bin/freecadcmd"; do
    [ -x "$c" ] && { printf '%s\n' "$c"; return 0; }
  done
  for n in FreeCADCmd freecadcmd; do
    c=$(command -v "$n" 2>/dev/null) && { printf '%s\n' "$c"; return 0; }
  done
  return 1
}

fc=$(find_freecadcmd) || {
  echo "csg2step.sh: FreeCADCmd not found (set \$FREECADCMD)" >&2
  exit 1
}

# Run the driver in human mode; capture everything (FreeCADCmd also prints its
# own banner, which we filter out via the marker block below).
output=$(CSG2STEP_IN="$in" CSG2STEP_OUT="$out" CSG2STEP_HUMAN=1 \
         "$fc" "$here/csg2step.py" 2>&1) || true

# Surface only the friendly block produced by csg2step.py's _emit_human().
block=$(printf '%s\n' "$output" \
        | sed -n '/^CSG2STEP_HUMAN_BEGIN$/,/^CSG2STEP_HUMAN_END$/p' \
        | sed '1d;$d')
status=$(printf '%s\n' "$output" | sed -n 's/^CSG2STEP_STATUS=//p' | tail -1)

if [ -z "$status" ]; then
  # No marker: the interpreter crashed or never reached emit(). Show a tail of
  # whatever it printed so the failure is not silent.
  echo "FAIL $in" >&2
  echo "  conversion crashed before producing a result; last output:" >&2
  printf '%s\n' "$output" | tail -n 15 | sed 's/^/  | /' >&2
  exit 1
fi

case "$status" in
  ok|suspect) printf '%s\n' "$block"; exit 0 ;;
  unsupported) printf '%s\n' "$block" >&2; exit 2 ;;
  empty) printf '%s\n' "$block" >&2; exit 3 ;;
  *) printf '%s\n' "$block" >&2; exit 1 ;;
esac
