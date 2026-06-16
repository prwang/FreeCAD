# SPDX-License-Identifier: LGPL-2.1-or-later

#***************************************************************************
#*   Copyright (c) 2021 Chris Hennes <chennes@pioneerlibrarysystem.org>    *
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU Lesser General Public License (LGPL)    *
#*   as published by the Free Software Foundation; either version 2 of     *
#*   the License, or (at your option) any later version.                   *
#*   for detail see the LICENSE text file.                                 *
#*                                                                         *
#*   This program is distributed in the hope that it will be useful,       *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU Library General Public License for more details.                  *
#*                                                                         *
#*   You should have received a copy of the GNU Library General Public     *
#*   License along with this program; if not, write to the Free Software   *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#*   USA                                                                   *
#*                                                                         *
#***************************************************************************

import unittest
import FreeCAD
import OpenSCAD
import importCSG
import tempfile
import os
import math

from os.path import join

__title__ = "ImportCSG OpenSCAD App unit tests"
__author__ = "Chris Hennes"
__url__ = "https://www.freecad.org"


class TestImportCSG(unittest.TestCase):

    MODULE = 'test_importCSG' # file name without extension
    temp_dir = tempfile.TemporaryDirectory()


    def setUp(self):
        self.test_dir = join(FreeCAD.getHomePath(), "Mod", "OpenSCAD", "OpenSCADTest", "data")

    def test_open_scad(self):
        testfile = join(self.test_dir, "CSG.scad")
        doc = importCSG.open(testfile)

        # Doc should now contain three solids: a union, an intersection, and a difference
        union = doc.getObject("union")
        intersection = doc.getObject("intersection")
        difference = doc.getObject("difference")

        self.assertTrue (union is not None)
        self.assertTrue (intersection is not None)
        self.assertTrue (difference is not None)

        FreeCAD.closeDocument("CSG")

    def test_open_csg(self):
        testfile = join(self.test_dir, "CSG.csg")
        doc = importCSG.open(testfile)

        # Doc should now contain three solids: a union, an intersection, and a difference
        union = doc.getObject("union")
        intersection = doc.getObject("intersection")
        difference = doc.getObject("difference")

        self.assertTrue (union is not None)
        self.assertTrue (intersection is not None)
        self.assertTrue (difference is not None)

        FreeCAD.closeDocument("CSG")

    def utility_create_scad(self, scadCode, name):
        filename = self.temp_dir.name + os.path.sep + name + ".scad"
        print (f"Creating {filename}")
        f = open(filename,"w+")
        f.write(scadCode)
        f.close()
        return importCSG.open(filename)

    def utility_create_csg(self, csgCode, name):
        # Unlike .scad, .csg files are parsed by importCSG directly and need
        # no OpenSCAD executable
        filename = self.temp_dir.name + os.path.sep + name + ".csg"
        print (f"Creating {filename}")
        f = open(filename,"w+")
        f.write(csgCode)
        f.close()
        return importCSG.open(filename)

    def utility_translate_x_csg(self, dx, body):
        return (f"multmatrix([[1, 0, 0, {dx}], [0, 1, 0, 0], "
                f"[0, 0, 1, 0], [0, 0, 0, 1]]) {{ {body} }}")

    def utility_intersection_of_cubes_csg(self, offsets):
        children = "\n".join(
            self.utility_translate_x_csg(dx, "cube(size = [10, 10, 10], center = false);")
            for dx in offsets)
        return "intersection() {\n" + children + "\n}\n"

    def utility_solid_roots(self, doc):
        return [o for o in doc.RootObjects
                if hasattr(o, "Shape") and not o.Shape.isNull() and o.Shape.Solids]

    # Regression tests: p_intersection_action used to run the eager
    # mycommon.Shape = mycommon.Base.Shape.common(...) unconditionally, but
    # .Base/.Tool only exist when the intersection has exactly two children.
    # Any other child count raised AttributeError during parse.
    def test_import_intersection_three_children(self):
        doc = self.utility_create_csg(
            self.utility_intersection_of_cubes_csg([0, 2, 4]),
            "intersection_three_children")
        obj = doc.getObject("intersection")
        self.assertIsNotNone(obj)
        self.assertFalse(obj.Shape.isNull())
        self.assertTrue(obj.Shape.isValid())
        self.assertEqual(len(obj.Shape.Solids), 1)
        # 10x10x10 cubes at x = 0, 2, 4 overlap in x = [4, 10]
        self.assertAlmostEqual(obj.Shape.Volume, 600.0, 6)
        FreeCAD.closeDocument(doc.Name)

    def test_import_intersection_four_children(self):
        doc = self.utility_create_csg(
            self.utility_intersection_of_cubes_csg([0, 2, 4, 6]),
            "intersection_four_children")
        obj = doc.getObject("intersection")
        self.assertIsNotNone(obj)
        self.assertAlmostEqual(obj.Shape.Volume, 400.0, 6)
        FreeCAD.closeDocument(doc.Name)

    def test_import_intersection_two_children(self):
        # guard: the (previously only working) eager 2-child branch
        doc = self.utility_create_csg(
            self.utility_intersection_of_cubes_csg([0, 2]),
            "intersection_two_children")
        obj = doc.getObject("intersection")
        self.assertIsNotNone(obj)
        self.assertAlmostEqual(obj.Shape.Volume, 800.0, 6)
        FreeCAD.closeDocument(doc.Name)

    def test_import_intersection_single_child(self):
        # single child passes through without an intersection feature
        doc = self.utility_create_csg(
            self.utility_intersection_of_cubes_csg([0]),
            "intersection_single_child")
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1)
        self.assertAlmostEqual(roots[0].Shape.Volume, 1000.0, 6)
        FreeCAD.closeDocument(doc.Name)

    def test_import_intersection_empty_operand(self):
        # Priority A: circle ∩ (empty square) is empty in OpenSCAD. A
        # square([0,0]) has a null shape and Shape.common() raises "Null input
        # shape", so the import aborted during parse. The result must be empty
        # -- crucially NOT a passthrough of the circle (A n 0 = 0, not A).
        csg = """
intersection() {
	circle($fn = 0, $fa = 12, $fs = 2, r = 5);
	square(size = [0, 0], center = true);
}
"""
        doc = self.utility_create_csg(csg, "intersection_empty_operand")
        nonempty = [o for o in doc.RootObjects
                    if hasattr(o, "Shape") and not o.Shape.isNull()]
        self.assertEqual(nonempty, [], [o.Name for o in nonempty])
        FreeCAD.closeDocument(doc.Name)

    # Regression test for the null-shape crash chain (ValueError: Null input
    # shape in fuse, minimized from a real-world model): linear_extrude over
    # offset() builds a lazy Part::Offset2D -> extrusion dependency chain,
    # and checkObjShape's single-level recompute could not resolve it before
    # the enclosing 2-child group fused the children.
    def test_import_fuse_of_offset_extrusions(self):
        child = """
	linear_extrude(height = 2, center = true, convexity = 1, scale = [1, 1], $fn = 16, $fa = 12, $fs = 2) {
		offset(r = 5, $fn = 16, $fa = 12, $fs = 2) {
			square(size = [10, 30], center = true);
		}
	}
"""
        doc = self.utility_create_csg("group() {" + child + child + "}",
                                      "fuse_of_offset_extrusions")
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1)
        self.assertTrue(roots[0].Shape.isValid())
        # both children coincide: (10*30 + perimeter*5 + pi*5^2) * height
        self.assertAlmostEqual(roots[0].Shape.Volume,
                               (300 + 400 + 25 * math.pi) * 2, delta=0.5)
        FreeCAD.closeDocument(doc.Name)

    def test_import_multmatrix_scale_no_source_leak(self):
        # A3#8 (surfaced via polyhedron-nonplanar-tests): a non-rigid
        # (scaling/shear) multmatrix takes the transformGeometry path in
        # p_multmatrix_action, which bakes the transformed shape into a new
        # Part::Feature but used to leave the untransformed source object as a
        # stray orphan document root -- so a scaled solid appeared twice (once
        # raw, once scaled), e.g. a polyhedron under a 0.02 scale leaked its
        # 206803-unit raw copy alongside the 1.65-unit scaled result.
        # A uniform scale 2 of a 10x10x10 cube must give ONE solid of volume
        # 8000 (10^3 * 2^3) and no leftover 1000-unit raw cube.
        csg = """
multmatrix([[2, 0, 0, 0], [0, 2, 0, 0], [0, 0, 2, 0], [0, 0, 0, 1]]) {
	cube(size = [10, 10, 10], center = false);
}
"""
        doc = self.utility_create_csg(csg, "multmatrix_scale_cube")
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1, [o.Name for o in doc.RootObjects])
        self.assertAlmostEqual(roots[0].Shape.Volume, 8000.0, delta=1e-3)
        FreeCAD.closeDocument(doc.Name)

    def test_import_resize_no_source_leak(self):
        # A4: p_resize_action bakes the resized shape into a new
        # Part::FeaturePython ("Matrix Deformation") via transformGeometry but
        # used to only ViewObject.hide() the source child, and only under gui.
        # Headless it left the un-resized source as a stray orphan document root,
        # so the source and the resized result both survived and the summed
        # solids double-counted (corpus resize-tests blew up by ~1e9 % when the
        # source had a huge extent). Same orphan-leak class as the multmatrix
        # fix. resize([4,0,0]) of a 2x2x2 cube scales X 2->4 and leaves Y,Z at 2
        # (OpenSCAD: a 0 newsize component means "leave that axis unchanged"),
        # so the result is ONE solid of volume 4*2*2 = 16 with no leftover
        # 8-unit raw cube.
        csg = """
resize(newsize = [4, 0, 0], auto = [0, 0, 0], convexity = 0) {
	cube(size = [2, 2, 2], center = false);
}
"""
        doc = self.utility_create_csg(csg, "resize_source_leak")
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1, [o.Name for o in doc.RootObjects])
        self.assertAlmostEqual(roots[0].Shape.Volume, 16.0, delta=1e-3)
        FreeCAD.closeDocument(doc.Name)

    def test_import_resize_negative_newsize(self):
        # A6: OpenSCAD leaves an axis unchanged when its target newsize is <= 0
        # (a 0 means "don't resize this axis"; a negative is likewise ignored,
        # NOT a mirror -- resize([-5,0,0]) cube(1) renders as the unit cube).
        # p_resize_action guarded only the exact string '0', so a negative value
        # ('-5') slipped through to factor -5 and produced a mirrored/scaled
        # solid of volume 5. With the numeric <= 0 guard, X is left unchanged
        # and the cube stays a unit cube of volume 1.
        csg = """
resize(newsize = [-5, 0, 0], auto = [0, 0, 0], convexity = 0) {
	cube(size = [1, 1, 1], center = false);
}
"""
        doc = self.utility_create_csg(csg, "resize_negative_newsize")
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1, [o.Name for o in doc.RootObjects])
        self.assertAlmostEqual(roots[0].Shape.Volume, 1.0, delta=1e-3)
        FreeCAD.closeDocument(doc.Name)

    def test_import_resize_auto(self):
        # A7: resize() auto-scale, matched to OpenSCAD 2021.01. The old code did
        # `if auto[r]: new_size[r] = new_size[0]`, which used the X target for
        # every auto axis and clobbered an axis that had BOTH auto AND its own
        # explicit newsize. OpenSCAD's rule: an axis with newsize>0 scales by
        # newsize/old; the autoscale factor is the MAX of those explicit factors;
        # an auto axis with newsize 0 takes that autoscale factor. Verified
        # against OpenSCAD renders on a 9x9x9 cube:
        #   [5,0,0]  auto [T,T,F] -> 5,5,9   = 225  (y follows x's 5/9)
        #   [5,0,20] auto [F,T,T] -> 5,20,20 = 2000 (y follows max(5/9,20/9)=20/9;
        #                                            z keeps its own 20)
        #   [6,0,0]  auto [T,T,T] -> 6,6,6   = 216  (uniform)
        def resize(newsize, auto):
            return (f"resize(newsize = {newsize}, auto = {auto}, convexity = 0) "
                    f"{{\n\tcube(size = [9, 9, 9], center = false);\n}}\n")
        for name, newsize, auto, expected in [
                ("resize_auto_partial", "[5, 0, 0]", "[1, 1, 0]", 225.0),
                ("resize_auto_on_explicit", "[5, 0, 20]", "[0, 1, 1]", 2000.0),
                ("resize_auto_uniform", "[6, 0, 0]", "[1, 1, 1]", 216.0)]:
            doc = self.utility_create_csg(resize(newsize, auto), name)
            roots = self.utility_solid_roots(doc)
            self.assertEqual(len(roots), 1, f"{name}: {[o.Name for o in doc.RootObjects]}")
            self.assertAlmostEqual(roots[0].Shape.Volume, expected, delta=1e-2,
                                   msg=name)
            FreeCAD.closeDocument(doc.Name)

    def test_import_projection_cut_false_no_plane_leak(self):
        # A3#9: p_projection_action built the helper "xy_plane_used_for_projection"
        # Part::Plane unconditionally, but only the cut=true branch consumes it
        # (into a MultiCommon). On the cut=false path (true projection, an
        # unsupported placeholder) the plane was never consumed and lingered as
        # a stray orphan document root -- a 10x10 face that pollutes the result.
        # The plane is now built inside the cut=true branch only.
        cut_false = """
projection(cut = false, convexity = 0) {
	cube(size = [10, 10, 10], center = true);
}
"""
        doc = self.utility_create_csg(cut_false, "projection_cut_false")
        leaked = [o for o in doc.Objects
                  if o.Name.startswith("xy_plane_used_for_projection")]
        self.assertEqual(leaked, [], "cut=false leaked the projection plane")
        FreeCAD.closeDocument(doc.Name)

        # cut=true is unaffected: the slice of a centered cube at z=0 is the
        # 10x10 mid-section, area 100, and the plane stays a consumed child.
        cut_true = """
projection(cut = true, convexity = 0) {
	cube(size = [10, 10, 10], center = true);
}
"""
        doc = self.utility_create_csg(cut_true, "projection_cut_true")
        roots = doc.RootObjects
        self.assertEqual(len(roots), 1, [o.Name for o in roots])
        self.assertFalse(roots[0].Shape.isNull())
        self.assertAlmostEqual(roots[0].Shape.Area, 100.0, delta=1e-3)
        FreeCAD.closeDocument(doc.Name)

    def test_import_linear_extrude_scale_taper(self):
        # A2#6: linear_extrude with a zero scale component tapers the top
        # profile to a line (one zero) or a point (both zero). OpenSCADFeatures
        # Twist.execute swept a pipe shell between the base wire and the
        # degenerate top wire, which raised "gp_Dir() - input vector has zero
        # norm", so the result imported as a null shape. It now builds the
        # tapered solid by connecting base perimeter vertices to their scaled
        # top vertices. Analytic: a 10x10 base extruded h=10 gives a pyramid
        # (scale [0,0]) of base*h/3 = 1000/3, and a wedge (scale [0,1]) of
        # base*h/2 = 500. Non-degenerate scale [0.5,0.5] is a frustum,
        # h/3*(A0+A1+sqrt(A0*A1)) = 10/3*(100+25+50) = 583.333, and must be
        # unaffected by the fix.
        def extrude(scale):
            return (f"linear_extrude(height = 10, center = false, convexity = 1, "
                    f"scale = {scale}, $fn = 0, $fa = 12, $fs = 2) {{\n"
                    f"\tsquare(size = [10, 10], center = false);\n}}\n")
        for name, scale, expected in [
                ("scale_taper_cone", "[0, 0]", 1000.0 / 3.0),
                ("scale_taper_wedge", "[0, 1]", 500.0),
                ("scale_taper_frustum", "[0.5, 0.5]", 583.3333333)]:
            doc = self.utility_create_csg(extrude(scale), name)
            roots = self.utility_solid_roots(doc)
            self.assertEqual(len(roots), 1, f"{name}: {[o.Name for o in doc.RootObjects]}")
            self.assertTrue(roots[0].Shape.isValid(), name)
            self.assertAlmostEqual(roots[0].Shape.Volume, expected, delta=1e-3,
                                   msg=name)
            FreeCAD.closeDocument(doc.Name)

    def test_import_linear_extrude_twist_scale_taper(self):
        # A5: linear_extrude with BOTH a twist and a zero scale component. A2#6
        # handled the no-twist taper, but its branch was gated on Angle==0, so a
        # twisted extrude whose top collapses to a POINT (scale [0,0]) fell
        # through to MakePipeShell, where the zero-area point top gave an
        # undefined sweep direction ("gp_Dir() zero norm") and the result
        # imported as a null shape. A point apex lies on the twist axis, so the
        # twist leaves it invariant: the solid is the straight pyramid base*h/3.
        # The one-zero (line) collapse already built on the MakePipeShell path
        # (its degenerate-but-nonzero top segment has a defined direction) and
        # must stay valid. Twist preserves cross-sectional area, so the volumes
        # equal the no-twist values: a 2x2 base extruded h=3 gives a pyramid
        # (twist 180, scale [0,0]) of base*h/3 = 4 and a wedge (twist 90,
        # scale [0,1]) of base*h/2 = 6.
        def extrude(twist, scale):
            return (f"linear_extrude(height = 3, center = false, convexity = 1, "
                    f"twist = {twist}, slices = 20, scale = {scale}, $fn = 0, "
                    f"$fa = 12, $fs = 2) {{\n"
                    f"\tsquare(size = [2, 2], center = false);\n}}\n")
        for name, twist, scale, expected in [
                ("twist_taper_point", 180, "[0, 0]", 4.0),
                ("twist_taper_line", 90, "[0, 1]", 6.0)]:
            doc = self.utility_create_csg(extrude(twist, scale), name)
            roots = self.utility_solid_roots(doc)
            self.assertEqual(len(roots), 1, f"{name}: {[o.Name for o in doc.RootObjects]}")
            self.assertTrue(roots[0].Shape.isValid(), name)
            self.assertAlmostEqual(roots[0].Shape.Volume, expected, delta=1e-3,
                                   msg=name)
            FreeCAD.closeDocument(doc.Name)

    def test_import_linear_extrude_twist_line_collapse(self):
        # A8: a twisted linear_extrude whose top collapses to a LINE (exactly one
        # zero scale component) is the case MakePipeShell cannot sweep for some
        # angles -- e.g. twist=180, scale=[0,1] raised in isReady()/build() and
        # the whole face loop aborted, leaving a null shape. For a single-wire
        # profile this now falls back to lofting through the rotated+scaled cross
        # sections, producing a valid solid. Twist preserves cross-sectional
        # area, so the volume converges to the smooth wedge base*h/2 = 2*2*3/2 = 6
        # (the discretized loft slightly overshoots, like OpenSCAD's own slices
        # render -- faceting-class, well within the band asserted here). The point
        # is that the geometry is no longer dropped to null.
        csg = """
linear_extrude(height = 3, center = false, convexity = 1, twist = 180, slices = 20, scale = [0, 1]) {
	square(size = [2, 2], center = false);
}
"""
        doc = self.utility_create_csg(csg, "twist_line_collapse")
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1, [o.Name for o in doc.RootObjects])
        self.assertTrue(roots[0].Shape.isValid())
        self.assertAlmostEqual(roots[0].Shape.Volume, 6.0, delta=0.6)
        FreeCAD.closeDocument(doc.Name)

    def test_import_background_modifier(self):
        # '%' subtrees are preview-only in OpenSCAD and must not contribute
        # geometry to the imported result (nor linger in the document)
        csg = """
union() {
	cube(size = [10, 10, 10], center = false);
%	multmatrix([[1, 0, 0, 20], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]) {
		cube(size = [5, 5, 5], center = false);
	}
}
"""
        doc = self.utility_create_csg(csg, "background_modifier")
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1)
        self.assertAlmostEqual(roots[0].Shape.Volume, 1000.0, 6)
        self.assertAlmostEqual(roots[0].Shape.BoundBox.XMax, 10.0, 6)
        self.assertEqual(len(doc.RootObjects), 1)
        FreeCAD.closeDocument(doc.Name)

    def test_import_debug_modifier(self):
        # '#' only highlights: geometry must still be included
        csg = """
union() {
	cube(size = [10, 10, 10], center = false);
#	multmatrix([[1, 0, 0, 20], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]) {
		cube(size = [5, 5, 5], center = false);
	}
}
"""
        doc = self.utility_create_csg(csg, "debug_modifier")
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1)
        self.assertAlmostEqual(roots[0].Shape.Volume, 1125.0, 6)
        FreeCAD.closeDocument(doc.Name)

    def test_import_booleans_unrefined(self):
        # imported booleans must not inherit Mod/Part RefineModel=true:
        # refine (removeSplitter) can corrupt the tangent/near-coincident
        # faces typical of OpenSCAD geometry into self-intersecting shells
        csg = """
difference() {
	union() {
		cube(size = [10, 10, 10], center = true);
		cube(size = [8, 8, 12], center = true);
	}
	cube(size = [2, 2, 30], center = true);
}
"""
        doc = self.utility_create_csg(csg, "booleans_unrefined")
        booleans = [o for o in doc.Objects
                    if o.TypeId in ("Part::Fuse", "Part::MultiFuse", "Part::Cut",
                                    "Part::Common", "Part::MultiCommon")]
        self.assertTrue(booleans)
        for o in booleans:
            self.assertFalse(o.Refine, f"{o.Name} should be unrefined")
        FreeCAD.closeDocument(doc.Name)

    def utility_2d_roots(self, doc):
        return [o for o in doc.RootObjects
                if hasattr(o, "Shape") and not o.Shape.isNull() and o.Shape.Faces]

    # Regression tests for 2D region semantics: OCC booleans tile overlapping
    # coplanar faces into fragments; OpenSCAD booleans operate on regions.
    # Without unification a downstream offset() offsets every fragment
    # separately (fillets silently lost) or BRepOffsetAPI_MakeOffset
    # segfaults outright.
    def test_import_union_2d_unified(self):
        csg = """
union() {
	square(size = [20, 4], center = true);
	square(size = [4, 20], center = true);
}
"""
        doc = self.utility_create_csg(csg, "union_2d_unified")
        roots = self.utility_2d_roots(doc)
        self.assertEqual(len(roots), 1)
        # one whole face, not a tiling of boolean fragments
        self.assertEqual(len(roots[0].Shape.Faces), 1)
        self.assertAlmostEqual(roots[0].Shape.Area, 144.0, 6)
        FreeCAD.closeDocument(doc.Name)

    def test_import_offset_fillet_closing(self):
        # offset(-r) offset(+r) of a 2D union = fillet the concave corners;
        # the cross has 4 of them, each adds r^2*(1 - pi/4)
        csg = """
offset(r = -1.5, $fn = 32, $fa = 12, $fs = 2) {
	offset(r = 1.5, $fn = 32, $fa = 12, $fs = 2) {
		union() {
			square(size = [20, 4], center = true);
			square(size = [4, 20], center = true);
		}
	}
}
"""
        doc = self.utility_create_csg(csg, "offset_fillet_closing")
        roots = self.utility_2d_roots(doc)
        self.assertEqual(len(roots), 1)
        self.assertEqual(len(roots[0].Shape.Faces), 1)
        expected = 144.0 + 4 * 1.5**2 * (1 - math.pi / 4)
        self.assertAlmostEqual(roots[0].Shape.Area, expected, 4)
        FreeCAD.closeDocument(doc.Name)

    def test_import_offset_chain_circle_hole(self):
        # offset-of-offset over a face with a circular hole: the first
        # offset's result carries the hole as a single closed circle edge,
        # which used to SIGSEGV BRepOffsetAPI_MakeOffset in the second
        csg = """
offset(r = -1, $fn = 64, $fa = 12, $fs = 2) {
	offset(r = 1, $fn = 64, $fa = 12, $fs = 2) {
		difference() {
			square(size = [20, 20], center = true);
			circle($fn = 64, $fa = 12, $fs = 2, r = 5);
		}
	}
}
"""
        doc = self.utility_create_csg(csg, "offset_chain_circle_hole")
        roots = self.utility_2d_roots(doc)
        self.assertEqual(len(roots), 1)
        self.assertEqual(len(roots[0].Shape.Faces), 1)
        # closing leaves the plain square with its r=5 hole unchanged
        self.assertAlmostEqual(roots[0].Shape.Area, 400 - 25 * math.pi, 4)
        FreeCAD.closeDocument(doc.Name)

    # Edge cases of offset(): OpenSCAD renders all of these EMPTY, the
    # importer used to crash (None deref / subobj[0] on a feature) or rely
    # on yacc error recovery for the childless semicolon form.
    def test_import_offset_childless(self):
        # `offset(r=1);` / `offset(r=1) {}` both compile to this csg form
        csg = """
offset(r = 1, $fn = 0, $fa = 12, $fs = 2);
cube(size = [5, 5, 5], center = false);
"""
        doc = self.utility_create_csg(csg, "offset_childless")
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1)
        self.assertAlmostEqual(roots[0].Shape.Volume, 125.0, 6)
        FreeCAD.closeDocument(doc.Name)

    def test_import_offset_background_only_child(self):
        # the '%' subtree is dropped, leaving the offset without children
        csg = """
offset(r = 1, $fn = 0, $fa = 12, $fs = 2) {
%	square(size = [5, 5], center = false);
}
cube(size = [5, 5, 5], center = false);
"""
        doc = self.utility_create_csg(csg, "offset_background_only")
        self.assertEqual(len(doc.RootObjects), 1)
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1)
        self.assertAlmostEqual(roots[0].Shape.Volume, 125.0, 6)
        FreeCAD.closeDocument(doc.Name)

    def test_import_offset_3d_child_ignored(self):
        # offset() is 2D-only: OpenSCAD warns 'Ignoring 3D child object for
        # 2D operation' and renders empty; the child must not leak either
        csg = """
offset(r = 1, $fn = 0, $fa = 12, $fs = 2) {
	cube(size = [5, 5, 5], center = false);
}
cube(size = [2, 2, 2], center = false);
"""
        doc = self.utility_create_csg(csg, "offset_3d_child")
        self.assertEqual(len(doc.RootObjects), 1,
                         [o.Name for o in doc.RootObjects])
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1)
        self.assertAlmostEqual(roots[0].Shape.Volume, 8.0, 6)
        FreeCAD.closeDocument(doc.Name)

    def test_import_offset_empty_child_is_empty(self):
        # Category C (t2d__offset-tests): offset() of an empty/degenerate 2D
        # region. square([0,0]) builds a null shape, and p_offset_action read
        # subobj.Shape.Volume on it -> RuntimeError "shape is invalid", aborting
        # the whole import. OpenSCAD renders offset() of an empty region as
        # empty; the sibling cube (vol 27) must survive.
        csg = """
offset(r = 1, $fn = 0, $fa = 12, $fs = 2) {
	square(size = [0, 0], center = false);
}
cube(size = [3, 3, 3], center = false);
"""
        doc = self.utility_create_csg(csg, "offset_empty_child")
        self.assertEqual(len(doc.RootObjects), 1,
                         [o.Name for o in doc.RootObjects])
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1)
        self.assertAlmostEqual(roots[0].Shape.Volume, 27.0, 6)
        FreeCAD.closeDocument(doc.Name)

    def test_import_rotate_extrude_unopenable_file_is_empty(self):
        # Category C (t3d__rotate_extrude-angle): the deprecated
        # rotate_extrude(file="...") 2D-profile import form. file="45" has no
        # extension/no such file -> process_import_file raised ValueError
        # "Unsupported file extension", aborting the whole import. OpenSCAD warns
        # and renders an unopenable file as empty; the sibling cube (vol 27)
        # must survive.
        csg = """
rotate_extrude(file = "45", layer = "", angle = 360, $fn = 0, $fa = 15, $fs = 4);
cube(size = [3, 3, 3], center = false);
"""
        doc = self.utility_create_csg(csg, "rotate_extrude_bad_file")
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1)
        self.assertAlmostEqual(roots[0].Shape.Volume, 27.0, 6)
        FreeCAD.closeDocument(doc.Name)

    def test_import_circle_not_leaked(self):
        # p_circle_action used to create the 'circle' object and then shadow
        # it with a second Draft.makeCircle object, orphaning the first as an
        # extra document root that polluted exports
        csg = """
linear_extrude(height = 2, center = false, convexity = 1, scale = [1, 1], $fn = 96, $fa = 12, $fs = 2) {
	difference() {
		square(size = [20, 20], center = true);
		circle($fn = 96, $fa = 12, $fs = 2, r = 5);
	}
}
"""
        doc = self.utility_create_csg(csg, "circle_not_leaked")
        self.assertEqual(len(doc.RootObjects), 1,
                         [o.Name for o in doc.RootObjects])
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1)
        # $fn=96 >= useMaxFN -> true circle: (400 - 25*pi) * 2
        self.assertAlmostEqual(roots[0].Shape.Volume,
                               (400 - 25 * math.pi) * 2, 4)
        FreeCAD.closeDocument(doc.Name)

    # --- Priority A regressions (minimized from the external real-world
    #     corpus; each pins one OpenSCAD semantic the importer got wrong) ---

    def test_import_circle_fractional_fn(self):
        # OpenSCAD rounds $fn to an integer fragment count; circle($fn = 0.1)
        # is legal and renders as a (near-)circle. p_circle_action used to do
        # int(p[3]['$fn']) -> int('0.1') -> ValueError during parse.
        doc = self.utility_create_csg(
            "circle($fn = 0.1, $fa = 12, $fs = 2, r = 10);",
            "circle_fractional_fn")
        circle = doc.getObject("circle")
        self.assertIsNotNone(circle)
        # round(0.1) == 0 -> n == 0 -> true (smooth) circle of radius 10
        self.assertAlmostEqual(circle.Shape.Area, math.pi * 100.0, delta=0.01)
        FreeCAD.closeDocument(doc.Name)

    def test_import_square_non_positive_is_empty(self):
        # Priority A: OpenSCAD renders a square with a non-positive dimension as
        # empty. The importer built a degenerate Part::Plane (an invalid or
        # bogus non-empty face -> square-tests read 107 vs the reference 7).
        # A 2x3 square unioned with a 1x0 (empty) square must yield just the
        # 2x3 area; the empty operand also exercises the fuse() null guard
        # (A u 0 = A) rather than crashing on "Null input shape".
        csg = """
union() {
	square(size = [2, 3], center = false);
	square(size = [1, 0], center = false);
}
"""
        doc = self.utility_create_csg(csg, "square_non_positive")
        roots = [o for o in doc.RootObjects
                 if hasattr(o, "Shape") and not o.Shape.isNull()]
        self.assertEqual(len(roots), 1)
        self.assertAlmostEqual(roots[0].Shape.Area, 6.0, delta=1e-6)
        FreeCAD.closeDocument(doc.Name)

    def test_import_union_drops_empty_operand(self):
        # Priority A (routing_tiles): a degenerate square([0,0]) is a null
        # operand (square fix); linear_extrude of it is empty, and that empty
        # must NOT null the enclosing union. Both linear_extrude and the
        # >2-child Part::MultiFuse now drop empty operands (A u 0 = A) and
        # consume them (no stray null roots) instead of propagating null. The
        # three real cubes (disjoint, x = 0/20/40) survive: volume 3000.
        csg = """
union() {
	cube(size = [10, 10, 10], center = false);
	multmatrix([[1, 0, 0, 20], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]) {
		cube(size = [10, 10, 10], center = false);
	}
	multmatrix([[1, 0, 0, 40], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]) {
		cube(size = [10, 10, 10], center = false);
	}
	linear_extrude(height = 2, center = false, convexity = 1, scale = [1, 1]) {
		square(size = [0, 0], center = false);
	}
}
"""
        doc = self.utility_create_csg(csg, "union_drops_empty")
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1)
        self.assertAlmostEqual(roots[0].Shape.Volume, 3000.0, 6)
        nulls = [o for o in doc.RootObjects
                 if hasattr(o, "Shape") and o.Shape.isNull()]
        self.assertEqual(nulls, [], [o.Name for o in nulls])
        FreeCAD.closeDocument(doc.Name)

    def test_repair_invalid_2d_face_for_fuse(self):
        # Category C (ex__module_recursion): a long chain of unions of
        # overlapping 2D faces can leave an operand face geometrically invalid
        # (mis-oriented inner wires); OCC then aborts the exact boolean with
        # "Unorientable shape"/"Bad orientation of sub-shape", killing the whole
        # import. repair2DFaces() reorients such a face (ShapeFix on a mutable
        # copy) so the boolean succeeds, preserving holes.
        #
        # Build a square([0,0]..[10,10]) with a same-orientation inner wire (a
        # hole that is NOT reversed) -> an invalid face that fuse() rejects. The
        # repair must yield a valid face of area 64 (100 - the 6x6 hole) and the
        # previously-failing fuse must then succeed.
        import Part
        V = FreeCAD.Vector
        outer = Part.makePolygon([V(0, 0, 0), V(10, 0, 0), V(10, 10, 0),
                                  V(0, 10, 0), V(0, 0, 0)])
        inner = Part.makePolygon([V(2, 2, 0), V(8, 2, 0), V(8, 8, 0),
                                  V(2, 8, 0), V(2, 2, 0)])
        bad = Part.Face([outer, inner])
        self.assertFalse(bad.isValid())
        # the exact boolean fails on the invalid operand (the C5 symptom)
        sq = Part.makePlane(5, 5, V(5, 5, 0))
        self.assertRaises(Exception, bad.fuse, sq)
        # repair reorients it: valid, hole preserved (area 64), fuse now works
        fixed = importCSG.repair2DFaces(bad)
        self.assertTrue(fixed.isValid())
        self.assertAlmostEqual(fixed.Area, 64.0, delta=1e-6)
        self.assertTrue(fixed.fuse(sq).isValid())
        # a valid face / a non-face must pass through untouched
        good = Part.makePlane(4, 4, V(0, 0, 0))
        self.assertIs(importCSG.repair2DFaces(good), good)
        box = Part.makeBox(1, 1, 1)
        self.assertIs(importCSG.repair2DFaces(box), box)

    def test_import_linear_extrude_empty_body_is_empty(self):
        # Category C (roundany__shell2d): linear_extrude of an empty body (a
        # multmatrix with no child block) evaluates to no geometry, exactly as
        # OpenSCAD renders it. The importer must produce zero shaped roots (and
        # no stray null roots) without raising -- the csg2step driver then
        # reports this as an 'empty' model rather than a hard error.
        csg = """
linear_extrude(height = 1, center = false, convexity = 1, scale = [1, 1], $fn = 0, $fa = 12, $fs = 2) {
	multmatrix([[1, 0, 0, 0], [0, 1, 0, -10], [0, 0, 1, 0], [0, 0, 0, 1]]);
}
"""
        doc = self.utility_create_csg(csg, "linear_extrude_empty_body")
        shaped = [o for o in doc.RootObjects
                  if hasattr(o, "Shape") and not o.Shape.isNull()]
        self.assertEqual(shaped, [], [o.Name for o in shaped])
        FreeCAD.closeDocument(doc.Name)

    def test_import_linear_extrude_polygon_undef_is_empty(self):
        # Category C (roundany__polyround): linear_extrude of
        # polygon(points=undef) -- the polygon is empty (205a619b6a), so the
        # extrude body is empty and the whole model evaluates to no geometry, as
        # OpenSCAD renders it. Zero shaped roots, no exception; the driver
        # reports 'empty', not an error.
        csg = """
linear_extrude(height = 3, center = false, convexity = 1, scale = [1, 1], $fn = 0, $fa = 12, $fs = 2) {
	polygon(points = undef, paths = undef, convexity = 1);
}
"""
        doc = self.utility_create_csg(csg, "linear_extrude_polygon_undef")
        shaped = [o for o in doc.RootObjects
                  if hasattr(o, "Shape") and not o.Shape.isNull()]
        self.assertEqual(shaped, [], [o.Name for o in shaped])
        FreeCAD.closeDocument(doc.Name)

    def test_import_non_finite_dimension(self):
        # Priority A: OpenSCAD emits inf/nan (e.g. from 1/0) as bare tokens in
        # compiled CSG, and its reader treats them as an unknown variable ->
        # undef. The lexer tokenised 'inf' as an identifier -> "syntax error
        # near 'inf'" -> PLY recovery dropped the whole statement, so a finite
        # primitive whose only oddity is $fn = inf (undef -> default facets in
        # OpenSCAD) vanished, and primitive-inf-tests imported as nothing. Now
        # inf/nan lex as NUMBER and the primitives guard non-finite values:
        #   - $fn = inf -> treated as unset -> smooth solid renders;
        #   - inf dimension/vertex -> empty (would otherwise build a degenerate
        #     OCC solid or throw "Failed to create face from wire").
        csg = """
cylinder($fn = inf, $fa = 12, $fs = 2, h = 2, r1 = 3, r2 = 3, center = false);
sphere($fn = 0, $fa = 12, $fs = 2, r = inf);
polyhedron(points = [[inf, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], faces = [[0, 1, 2], [0, 2, 3], [0, 3, 1], [1, 3, 2]], convexity = 1);
"""
        doc = self.utility_create_csg(csg, "non_finite_dim")
        # the inf-$fn cylinder survives the parse and renders smooth: V = pi r^2 h
        cyl = doc.getObject("cylinder")
        self.assertIsNotNone(cyl)
        self.assertFalse(cyl.Shape.isNull())
        self.assertAlmostEqual(cyl.Shape.Volume, math.pi * 9.0 * 2.0, delta=1e-6)
        # the inf-radius sphere is empty
        sph = doc.getObject("sphere")
        self.assertIsNotNone(sph)
        self.assertTrue(sph.Shape.isNull() or sph.Shape.Volume == 0.0)
        # the inf-vertex polyhedron is empty (no crash building the face)
        poly = doc.getObject("polyhedron")
        self.assertIsNotNone(poly)
        self.assertTrue(poly.Shape.isNull() or poly.Shape.Volume == 0.0)
        FreeCAD.closeDocument(doc.Name)

    def test_import_intersection_multi_in_linear_extrude(self):
        # shape of the real-world failure: a >2-child 2D intersection whose
        # result is consumed by linear_extrude before any document recompute
        squares = "\n".join(
            self.utility_translate_x_csg(dx, "square(size = [10, 10], center = false);")
            for dx in [0, 2, 4])
        csg = ("linear_extrude(height = 2, center = false, convexity = 1, scale = [1, 1]) {\n"
               "intersection() {\n" + squares + "\n}\n}\n")
        doc = self.utility_create_csg(csg, "intersection_multi_extrude")
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1)
        # 6 x 10 overlap extruded to height 2
        self.assertAlmostEqual(roots[0].Shape.Volume, 120.0, 6)
        FreeCAD.closeDocument(doc.Name)

    def test_import_sphere(self):
        doc = self.utility_create_scad("sphere(10.0);","sphere")
        sphere = doc.getObject("sphere")
        self.assertTrue (sphere is not None)
        self.assertTrue (sphere.Radius == 10.0)
        FreeCAD.closeDocument(doc.Name)

    def test_import_cylinder(self):
        doc = self.utility_create_scad("cylinder(50.0,d=10.0);","cylinder")
        cylinder = doc.getObject("cylinder")
        self.assertTrue (cylinder is not None)
        self.assertTrue (cylinder.Radius == 5.0)
        self.assertTrue (cylinder.Height == 50.0)
        FreeCAD.closeDocument(doc.Name)

    def test_import_cube(self):
        doc = self.utility_create_scad("cube([1.0,2.0,3.0]);","cube")
        cube = doc.getObject("cube")
        self.assertTrue (cube is not None)
        self.assertTrue (cube.Length == 1.0)
        self.assertTrue (cube.Width == 2.0)
        self.assertTrue (cube.Height == 3.0)
        FreeCAD.closeDocument(doc.Name)

    def test_import_circle(self):
        doc = self.utility_create_scad("circle(10.0);","circle")
        circle = doc.getObject("circle")
        self.assertTrue (circle is not None)
        self.assertTrue (circle.Radius == 10.0)
        FreeCAD.closeDocument(doc.Name)

    def test_import_square(self):
        doc = self.utility_create_scad("square([1.0,2.0]);","square")
        square = doc.getObject("square")
        self.assertTrue (square is not None)
        self.assertTrue (square.Length == 1.0)
        self.assertTrue (square.Width == 2.0)
        FreeCAD.closeDocument(doc.Name)

    def test_import_text(self):
        # This uses the DXF importer that may pop-up modal dialogs
        # if not all 3rd party libraries are installed
        if FreeCAD.GuiUp:
            return
        try:
            doc = self.utility_create_scad("text(\"X\");","text") # Keep it short to keep the test fast-ish
            text = doc.getObject("text")
            self.assertTrue (text is not None)
            FreeCAD.closeDocument(doc.Name)
        except Exception:
            return # We may not have the DXF importer available

        # Try a number with a set script:
        doc = self.utility_create_scad("text(\"2\",script=\"latin\");","two_text")
        text = doc.getObject("text")
        self.assertTrue (text is not None)
        FreeCAD.closeDocument(doc.Name)

        # Leave off the script (which is supposed to default to "latin")
        doc = self.utility_create_scad("text(\"1\");","one_text")
        text = doc.getObject("text")
        self.assertTrue (text is not None)
        FreeCAD.closeDocument(doc.Name)

    def test_import_polygon_nopath(self):
        doc = self.utility_create_scad("polygon(points=[[0,0],[100,0],[130,50],[30,50]]);","polygon_nopath")
        polygon = doc.getObject("polygon")
        self.assertTrue (polygon is not None)
        self.assertAlmostEqual (polygon.Shape.Area, 5000.0)
        FreeCAD.closeDocument(doc.Name)

    def test_import_polygon_path(self):
        doc = self.utility_create_scad("polygon([[0,0],[100,0],[130,50],[30,50]], paths=[[0,1,2,3]]);","polygon_path")
        wire = doc.ActiveObject # With paths, the polygon gets created as a wire...
        self.assertTrue (wire is not None)
        self.assertAlmostEqual (wire.Shape.Area, 5000.0)
        FreeCAD.closeDocument(doc.Name)

    def test_import_polygon_undef_is_empty(self):
        # Priority A: OpenSCAD emits polygon(points = undef, paths = undef, ...)
        # for a polygon with no geometry (pervasive in Round-Anything library
        # code). No grammar rule matched "points = undef", so it raised a
        # (silently swallowed) syntax error. Recognise it as an empty result
        # instead; assert that no syntax error fires and the sibling cube still
        # imports while the empty polygon contributes nothing.
        calls = []
        orig_p_error = importCSG.p_error
        importCSG.p_error = lambda p: calls.append(getattr(p, "value", p))
        try:
            doc = self.utility_create_csg(
                "cube(size = [10, 10, 10], center = false);\n"
                "polygon(points = undef, paths = undef, convexity = 1);\n",
                "polygon_undef")
        finally:
            importCSG.p_error = orig_p_error
        self.assertEqual(calls, [], "polygon(points=undef) must not be a syntax error")
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1)
        self.assertAlmostEqual(roots[0].Shape.Volume, 1000.0, 6)
        FreeCAD.closeDocument(doc.Name)

    def test_import_polygon_with_hole(self):
        # Priority A: a polygon with an outer path plus hole path(s). The loop
        # built a separate face per path and pushed it from *inside* the loop
        # ("This only pushes last polygon"), so the holes were dropped and only
        # the last sub-path survived. OpenSCAD fills the paths by the even-odd
        # rule: here a 10x10 outer with a 4x4 hole -> area 100 - 16 = 84.
        csg = ("polygon(points = [[0, 0], [10, 0], [10, 10], [0, 10], "
               "[3, 3], [7, 3], [7, 7], [3, 7]], "
               "paths = [[0, 1, 2, 3], [4, 5, 6, 7]], convexity = 1);\n")
        doc = self.utility_create_csg(csg, "polygon_with_hole")
        obj = doc.ActiveObject
        self.assertIsNotNone(obj)
        self.assertAlmostEqual(obj.Shape.Area, 84.0, delta=1e-6)
        # one face with one outer wire and one inner (hole) wire
        self.assertEqual(len(obj.Shape.Faces), 1)
        self.assertEqual(len(obj.Shape.Wires), 2)
        FreeCAD.closeDocument(doc.Name)

    def test_import_polyhedron(self):
        doc = self.utility_create_scad(
"""
polyhedron(
  points=[ [10,10,0],[10,-10,0],[-10,-10,0],[-10,10,0], // the four points at base
           [0,0,10]  ],                                 // the apex point
  faces=[ [0,1,4],[1,2,4],[2,3,4],[3,0,4],              // each triangle side
              [1,0,3],[2,1,3] ]                         // two triangles for square base
 );
""","polyhedron"
                )
        polyhedron = doc.ActiveObject # With paths, the polygon gets created as a wire...
        self.assertTrue (polyhedron is not None)
        self.assertAlmostEqual (polyhedron.Shape.Volume, 1333.3333, 4)
        FreeCAD.closeDocument(doc.Name)

    def test_import_difference(self):
        doc = self.utility_create_scad("difference() { cube(15, center=true); sphere(10); }", "difference")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Volume, 266.1323, 3)
        FreeCAD.closeDocument(doc.Name)

    def test_import_intersection(self):
        doc = self.utility_create_scad("intersection() { cube(15, center=true); sphere(10); }", "intersection")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Volume, 3108.8677, 3)
        FreeCAD.closeDocument(doc.Name)

    def test_import_union(self):
        doc = self.utility_create_scad("union() { cube(15, center=true); sphere(10); }", "union")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Volume, 4454.9224, 3)
        FreeCAD.closeDocument(doc.Name)

    def test_import_rotate_extrude(self):
        doc = self.utility_create_scad("rotate_extrude() translate([10, 0]) square(5);", "rotate_extrude_simple")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Volume, 1963.4954, 3)
        FreeCAD.closeDocument(doc.Name)

        doc = self.utility_create_scad("translate([0, 30, 0]) rotate_extrude() polygon( points=[[0,0],[8,4],[4,8],[4,12],[12,16],[0,20]] );", "rotate_extrude_no_hole")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Volume, 2412.7431, 3)
        FreeCAD.closeDocument(doc.Name)

        # Bug #4353 - https://tracker.freecad.org/view.php?id=4353
        doc = self.utility_create_scad("rotate_extrude($fn=4, angle=180) polygon([[0,0],[3,3],[0,3]]);", "rotate_extrude_low_fn")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Volume, 9.0, 5)
        FreeCAD.closeDocument(doc.Name)

        doc = self.utility_create_scad("rotate_extrude($fn=4, angle=-180) polygon([[0,0],[3,3],[0,3]]);", "rotate_extrude_low_fn_negative_angle")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Volume, 9.0, 5)
        FreeCAD.closeDocument(doc.Name)

        doc = self.utility_create_scad("rotate_extrude(angle=180) polygon([[0,0],[3,3],[0,3]]);", "rotate_extrude_angle")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Volume, 4.5*math.pi, 5)
        FreeCAD.closeDocument(doc.Name)

        doc = self.utility_create_scad("rotate_extrude(angle=-180) polygon([[0,0],[3,3],[0,3]]);", "rotate_extrude_negative_angle")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Volume, 4.5*math.pi, 5)
        FreeCAD.closeDocument(doc.Name)

    def test_import_rotate_extrude_childless(self):
        # Priority A: OpenSCAD compiles a childless rotate_extrude(...) to the
        # semicolon form with no 'file' kwarg. It revolves nothing and renders
        # empty. The importer assumed a 'file' kwarg, so p[3]['file'] raised
        # KeyError and aborted the whole import. The surrounding cube must still
        # come through, and the empty rotate_extrude must add no geometry.
        csg = """
union() {
	cube(size = [10, 10, 10], center = false);
	rotate_extrude(angle = 360, convexity = 2, $fn = 0, $fa = 12, $fs = 2);
}
"""
        doc = self.utility_create_csg(csg, "rotate_extrude_childless")
        roots = self.utility_solid_roots(doc)
        self.assertEqual(len(roots), 1)
        self.assertAlmostEqual(roots[0].Shape.Volume, 1000.0, 6)
        FreeCAD.closeDocument(doc.Name)

    def test_import_linear_extrude(self):
        doc = self.utility_create_scad("linear_extrude(height = 20) square([20, 10], center = true);", "linear_extrude_simple")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Volume, 4000.000, 3)
        FreeCAD.closeDocument(doc.Name)

        doc = self.utility_create_scad("linear_extrude(height = 20, twist = 90) square([20, 10], center = true);", "linear_extrude_twist")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Volume, 4000.000, 2)
        FreeCAD.closeDocument(doc.Name)

        doc = self.utility_create_scad("linear_extrude(height = 20, scale = 0.2) square([20, 10], center = true);", "linear_extrude_scale")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        h = 20
        a1 = 20*10
        a2 = 20*0.2 * 10*0.2
        expected_volume = (h/3) * (a1+a2+math.sqrt(a1*a2))
        self.assertAlmostEqual (object.Shape.Volume, expected_volume, 3)
        FreeCAD.closeDocument(doc.Name)

        doc = self.utility_create_scad("linear_extrude(height = 20, twist = 180, scale=0.2) square([20, 10], center = true);", "linear_extrude_twist_scale")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Volume, expected_volume, 2)
        FreeCAD.closeDocument(doc.Name)

    def test_import_rotate_extrude_file(self):
        # OpenSCAD doesn't seem to have this feature at this time (March 2021)
        pass

# There is a problem with the DXF code right now, it doesn't like this square.
#    def test_import_import_dxf(self):
#        testfile = join(self.test_dir, "Square.dxf").replace('\\','/')
#        doc = self.utility_create_scad("import(\"{}\");".format(testfile), "import_dxf");
#        object = doc.ActiveObject
#        self.assertTrue (object is not None)
#        FreeCAD.closeDocument(doc.Name)

    def test_import_import_stl(self):
        preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/OpenSCAD")
        transfer_mechanism = preferences.GetInt('transfermechanism',0)
        if transfer_mechanism == 2:
            print ("Cannot test STL import, communication with OpenSCAD is via pipes")
            print ("If either OpenSCAD or FreeCAD are installed as sandboxed packages,")
            print ("use of import is not possible.")
            return
        testfile = join(self.test_dir, "Cube.stl").replace('\\','/')
        doc = self.utility_create_scad("import(\"{}\");".format(testfile), "import_stl");
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        FreeCAD.closeDocument(doc.Name)

    def test_import_resize(self):
        doc = self.utility_create_scad("resize([2,2,2]) cube();", "resize_simple")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Volume, 8.000000, 6)
        FreeCAD.closeDocument(doc.Name)

        doc = self.utility_create_scad("resize([2,2,0]) cube();", "resize_with_zero")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Volume, 4.000000, 6)
        FreeCAD.closeDocument(doc.Name)

        doc = self.utility_create_scad("resize([2,0,0], auto=true) cube();", "resize_with_auto")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Volume, 8.000000, 6)
        FreeCAD.closeDocument(doc.Name)

        doc = self.utility_create_scad("resize([2,2,2]) cube([2,2,2]);", "resize_no_change")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Volume, 8.000000, 6)
        FreeCAD.closeDocument(doc.Name)

        doc = self.utility_create_scad("resize([2,2,2]) cube([4,8,12]);", "resize_non_uniform")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Volume, 8.000000, 6)
        FreeCAD.closeDocument(doc.Name)

        # Make sure to test something that isn't just a box (where the bounding box is trivial)
        doc = self.utility_create_scad("""
resize(newsize = [0,0,10], auto = [0,0,0]) {
    sphere($fn = 96, $fa = 12, $fs = 2, r = 8.5);
}""", "resize_non_uniform_sphere")
        object = doc.ActiveObject
        self.assertTrue (object is not None)
        object.Shape.tessellate(0.025) # To ensure the bounding box calculation is correct
        self.assertAlmostEqual (object.Shape.BoundBox.XLength, 2*8.5, 1)
        self.assertAlmostEqual (object.Shape.BoundBox.YLength, 2*8.5, 1)
        self.assertAlmostEqual (object.Shape.BoundBox.ZLength, 10.0, 1)
        FreeCAD.closeDocument(doc.Name)

    def test_import_resize_zero_extent_axis(self):
        # Priority A: resize() of a shape with a zero-extent axis. A 2D square
        # has ZLength == 0, so the old transform divided new_size[z]/0 ->
        # ZeroDivisionError, aborting the import. OpenSCAD leaves a zero-extent
        # axis unscaled; here the square just stretches 10x10 -> 15x15 in XY.
        csg = """
resize(newsize = [15, 15, 0], auto = [0, 0, 0], convexity = 0) {
	square(size = [10, 10], center = false);
}
"""
        doc = self.utility_create_csg(csg, "resize_zero_extent_axis")
        obj = doc.ActiveObject
        self.assertIsNotNone(obj)
        self.assertAlmostEqual(obj.Shape.Area, 225.0, delta=0.01)
        FreeCAD.closeDocument(doc.Name)

    def test_import_surface(self):
        preferences = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/OpenSCAD")
        transfer_mechanism = preferences.GetInt('transfermechanism',0)
        if transfer_mechanism == 2:
            print ("Cannot test .dat surface import, communication with OpenSCAD is via pipes")
            print ("If either OpenSCAD or FreeCAD are installed as sandboxed packages, use of")
            print ("import is not possible.")
            return
        # Workaround for absolute vs. relative path issue
        # Inside the OpenSCAD file an absolute path name to Surface.dat is used
        # but by using the OpenSCAD executable to create a CSG file it's converted
        # into a path name relative to the output filename.
        # In order to open the CAG file correctly the cwd must be temporarily changed
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = os.getcwd()
            os.chdir(temp_dir)
            try:
                testfile = join(self.test_dir, "Surface.dat").replace('\\','/')
                doc = self.utility_create_scad(f"surface(file = \"{testfile}\", center = true, convexity = 5);", "surface_simple_dat")
                object = doc.ActiveObject
                self.assertTrue (object is not None)
                self.assertAlmostEqual (object.Shape.Volume, 275.000000, 6)
                self.assertAlmostEqual (object.Shape.BoundBox.XMin, -4.5, 6)
                self.assertAlmostEqual (object.Shape.BoundBox.XMax, 4.5, 6)
                self.assertAlmostEqual (object.Shape.BoundBox.YMin, -4.5, 6)
                self.assertAlmostEqual (object.Shape.BoundBox.YMax, 4.5, 6)
                FreeCAD.closeDocument(doc.Name)

                testfile = join(self.test_dir, "Surface.dat").replace('\\','/')
                doc = self.utility_create_scad(f"surface(file = \"{testfile}\", convexity = 5);", "surface_uncentered_dat")
                object = doc.ActiveObject
                self.assertTrue (object is not None)
                self.assertAlmostEqual (object.Shape.Volume, 275.000000, 6)
                self.assertAlmostEqual (object.Shape.BoundBox.XMin, 0, 6)
                self.assertAlmostEqual (object.Shape.BoundBox.XMax, 9, 6)
                self.assertAlmostEqual (object.Shape.BoundBox.YMin, 0, 6)
                self.assertAlmostEqual (object.Shape.BoundBox.YMax, 9, 6)
                FreeCAD.closeDocument(doc.Name)

                testfile = join(self.test_dir, "Surface2.dat").replace('\\','/')
                doc = self.utility_create_scad(f"surface(file = \"{testfile}\", center = true, convexity = 5);", "surface_rectangular_dat")
                object = doc.ActiveObject
                self.assertTrue (object is not None)
                self.assertAlmostEqual (object.Shape.Volume, 24.5500000, 6)
                self.assertAlmostEqual (object.Shape.BoundBox.XMin, -2, 6)
                self.assertAlmostEqual (object.Shape.BoundBox.XMax, 2, 6)
                self.assertAlmostEqual (object.Shape.BoundBox.YMin, -1.5, 6)
                self.assertAlmostEqual (object.Shape.BoundBox.YMax, 1.5, 6)
                FreeCAD.closeDocument(doc.Name)
            except:
                os.chdir(cwd)
                raise Exception
            else:
                os.chdir(cwd)

    def test_import_projection(self):
        base_shape = "linear_extrude(height=5,center=true,twist=90,scale=0.5){square([1,1],center=true);}"
        hole = "cube([0.25,0.25,6],center=true);"
        cut_shape = f"difference() {{ {base_shape} {hole} }}"

        doc = self.utility_create_scad(f"projection(cut=true) {base_shape}", "projection_slice_square")
        object = doc.getObject("projection_cut")
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Area, 0.75*0.75, 3)
        FreeCAD.closeDocument(doc.Name)

        doc = self.utility_create_scad(f"projection(cut=true) {cut_shape}", "projection_slice_square_with_hole")
        object = doc.getObject("projection_cut")
        self.assertTrue (object is not None)
        self.assertAlmostEqual (object.Shape.Area, 0.75*0.75 - 0.25*0.25, 3)
        FreeCAD.closeDocument(doc.Name)

        # Unimplemented functionality:

        # With cut=false, the twisted unit square projects to a circle of radius sqrt(0.5)
        #doc = self.utility_create_scad(f"projection(cut=false) {base_shape}", "projection_circle")
        #object = doc.getObject("projection")
        #self.assertTrue (object is not None)
        #self.assertAlmostEqual (object.Shape.Area, 2*math.pi*math.sqrt(2), 3)
        #FreeCAD.closeDocument(doc.Name)

        #doc = self.utility_create_scad(f"projection(cut=false) {cut_shape}", "projection_circle_with_hole")
        #object = doc.getObject("projection")
        #self.assertTrue (object is not None)
        #self.assertAlmostEqual (object.Shape.Area, 2*math.pi*math.sqrt(0.5) - 0.125, 3)
        #FreeCAD.closeDocument(doc.Name)

    def test_import_hull(self):
        pass

    def test_import_minkowski(self):
        pass

    def test_import_offset(self):
        pass

    def test_empty_union(self):
        content = """union() {
 color(c = [0.30, 0.50, 0.80, 0.50]) {
  union() {
   union() {
    union() {
     translate(v = [23.0, -9.50, 13.60]) {
      union() {
       difference() {
        difference() {
         difference() {
          difference() {
           difference() {
            difference() {
             difference() {
              union() {
               union() {
                union() {
                 union() {
                  union() {
                   union() {
                    union() {
                     union();
                     translate(v = [2.50, 2.50, 9.50]) {
                      cylinder(h = 19.0, r = 2.50, center = true, $fn = 100);
                     }
                    }
                    translate(v = [11.50, 2.50, 9.50]) {
                     cylinder(h = 19.0, r = 2.50, center = true, $fn = 100);
                    }
                   }
                   translate(v = [11.50, 6.30, 9.50]) {
                    cylinder(h = 19.0, r = 2.50, center = true, $fn = 100);
                   }
                  }
                  translate(v = [2.50, 6.30, 9.50]) {
                   cylinder(h = 19.0, r = 2.50, center = true, $fn = 100);
                  }
                 }
                 translate(v = [2.50, 0.0, 0.0]) {
                  cube(size = [9.0, 8.80, 19.0]);
                 }
                }
                translate(v = [0.0, 2.50, 0.0]) {
                 cube(size = [14.0, 3.80, 19.0]);
                }
               }
              }
              translate(v = [-1.0, 8.40, 3.50]) {
               cube(size = [30.0, 10.0, 12.0]);
              }
             }
             translate(v = [4.0, 4.0, -0.10]) {
              cylinder($fn = 30, h = 20.0, r = 1.750, r1 = 1.80);
             }
            }
            translate(v = [9.0, 4.40, -0.10]) {
             cylinder($fn = 30, h = 20.0, r = 2.150, r1 = 2.20);
            }
           }
           translate(v = [12.30, 2.10, -0.10]) {
            cube(size = [5.0, 2.20, 20.0]);
           }
          }
          translate(v = [1.90, 7.60, -0.10]) {
           cube(size = [2.20, 5.0, 20.0]);
          }
         }
         translate(v = [3.60, 7.20, 1.80]) {
          cube(size = [30.0, 10.0, 2.0]);
         }
        }
        translate(v = [0, 0, 13.40]) {
         translate(v = [3.60, 7.20, 1.80]) {
          cube(size = [30.0, 10.0, 2.0]);
         }
        }
       }
      }
     }
    }
   }
  }
 }
}"""
        doc = self.utility_create_scad(content, "empty_union")
        self.assertEqual (len(doc.RootObjects), 1)
        FreeCAD.closeDocument(doc.Name)

    def test_complex_fuse_no_placement(self):
        # Issue #7878 - https://github.com/FreeCAD/FreeCAD/issues/7878

        csg_data = """
group() {
    multmatrix([[1, 0, 0, 0], [0, 1, 0, -127], [0, 0, 1, -6], [0, 0, 0, 1]]) {
        union() {
            group() {
                difference() {
                    cube(size = [4, 106.538, 12], center = false);
                    group() {
                            polyhedron(points = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [0, 1, 1]], faces = [[0, 1, 2], [5, 4, 3], [3, 1, 0], [1, 3, 4], [0, 2, 3], [5, 3, 2], [4, 2, 1], [2, 4, 5]], convexity = 1);
                    }
                }
            }
            polyhedron(points = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [0, 1, 1]], faces = [[0, 1, 2], [5, 4, 3], [3, 1, 0], [1, 3, 4], [0, 2, 3], [5, 3, 2], [4, 2, 1], [2, 4, 5]], convexity = 1);
            polyhedron(points = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [0, 1, 1]], faces = [[0, 1, 2], [5, 4, 3], [3, 1, 0], [1, 3, 4], [0, 2, 3], [5, 3, 2], [4, 2, 1], [2, 4, 5]], convexity = 1);
        }
    }
    multmatrix([[1, 0, 0, 6.4], [0, 1, 0, -125], [0, 0, 1, -40], [0, 0, 0, 1]]) {
        difference() {
            cylinder($fn = 0, $fa = 12, $fs = 2, h = 80, r1 = 8, r2 = 8, center = false);
            multmatrix([[1, 0, 0, -14.4], [0, 1, 0, -8], [0, 0, 1, -5], [0, 0, 0, 1]]) {
                cube(size = [8, 16, 90], center = false);
            }
        }
    }
}
"""
        doc = self.utility_create_scad(csg_data, "complex-fuse")
        self.assertEqual (doc.RootObjects[0].Placement, FreeCAD.Placement())
        FreeCAD.closeDocument(doc.Name)
