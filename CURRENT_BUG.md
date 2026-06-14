# CURRENT_BUG — A7: resize() auto-scale rule does not match OpenSCAD

## Observation
- `p_resize_action`'s auto handling (`if auto[r]=='1': new_size[r]=new_size[0]`)
  is wrong: it sets an auto axis's target to the X target value, and clobbers an
  axis that has BOTH auto=true AND its own explicit newsize. Result diverges from
  OpenSCAD on the resize test files (dominant residual of `t3d__resize-tests`,
  `t2d__resize-2d-tests`).
- Previously parked as "UNKNOWN / implementation-defined" — WRONG: OpenSCAD's
  rule is concrete and deterministic.

## Evidence — OpenSCAD 2021.01 render battery (cube([9,9,9]) base)
| newsize | auto | OpenSCAD vol | implied factors |
|---|---|---|---|
| [5,0,0]  | [T,T,F] | 225  | x 5/9, y 5/9 (auto), z 1 |
| [5,0,20] | [F,T,T] | 2000 | x 5/9, y 20/9 (auto), z 20/9 |
| [6,0,0]  | [T,T,T] | 216  | uniform 6/9 |
| [5,0,20] | [F,T,F] | 2000 | x 5/9, y 20/9 (auto), z 20/9 |
| [0,6,0]  | [T,F,T] | 216  | uniform 6/9 |
| [10,0,0] | [F,T,T] | 1000 | uniform 10/9 |

## Verdict — OpenSCAD 2021.01 resize algorithm (ACCEPTED, fits all 6)
```
old = bbox extents
explicit_factors = { newsize[i]/old[i] : newsize[i] > 0 and old[i] > 0 }
autoscale = max(explicit_factors)               # the LARGEST explicit factor
for each axis i:
    if newsize[i] > 0 and old[i] > 0:  factor = newsize[i]/old[i]
    elif newsize[i] == 0 and auto[i] and old[i] > 0 and explicit_factors:
                                       factor = autoscale
    else:                              factor = 1.0     # unchanged
```
- An auto axis with newsize 0 follows the MAX explicit factor (not X's value, not
  a per-axis factor). An axis with its own newsize>0 ignores auto. newsize ≤ 0 on
  a non-auto axis is left unchanged (subsumes the A6 negative fix). Zero-extent
  axes (2D z) are left unchanged. "Right anyway": this is OpenSCAD's documented
  proportional-autoscale behaviour; FreeCAD should match it exactly.

## Fix
- Replace the auto/zero for-loop AND the `factors=[...]` list in `p_resize_action`
  with the algorithm above. Verify FreeCAD .step volumes match the battery and
  the resize corpus cases converge.
