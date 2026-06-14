// SYMPTOM: importing this aborted the WHOLE file during parse with
//   ValueError: invalid literal for int() with base 10: '0.1'
//   $fn is a fragment count; OpenSCAD compiles it verbatim as $fn = 0.1.
// CAUSE: p_circle_action did int(p[3]['$fn']) -> int('0.1') raises (it does not
//   truncate a decimal string). p_cylinder_action already rounded; circle did not.
// FIX: importCSG.py p_circle_action -> n = int(round(float(p[3]['$fn']))).
//   Commit bc822b9446.
// EXPECTED (OpenSCAD): $fn rounds to an integer; round(0.1) = 0 -> $fn unset ->
//   fall back to $fa/$fs -> a smooth circle of radius 10, area = pi*r^2 = 100*pi.
circle($fn = 0.1, r = 10);
