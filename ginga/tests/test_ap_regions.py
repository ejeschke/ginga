"""Test ap_regions.py"""

import numpy as np
import pytest

regions = pytest.importorskip('regions')

from astropy import units as u

from ginga.util.ap_region import (astropy_region_to_ginga_canvas_object as r2g,
                                  ginga_canvas_object_to_astropy_region as g2r)
from ginga.canvas.CanvasObject import get_canvas_types


dc = get_canvas_types()


class Test_R2G(object):
    """Test conversions from AstroPy regions to Ginga canvas types."""

    def test_point1(self):
        r = regions.PointPixelRegion(center=regions.PixCoord(x=42, y=43),
                                     visual=regions.RegionVisual(symbol='x'))
        o = r2g(r)
        assert isinstance(o, dc.Point) and o.style == 'cross'
        assert np.all(np.isclose((o.x, o.y), (r.center.x, r.center.y)))

    def test_point2(self):
        r = regions.PointPixelRegion(center=regions.PixCoord(x=42, y=43),
                                     visual=regions.RegionVisual(symbol='+'))
        o = r2g(r)
        assert isinstance(o, dc.Point) and o.style == 'plus'

    def test_point3(self):
        r = regions.PointPixelRegion(center=regions.PixCoord(x=42, y=43),
                                     visual=regions.RegionVisual(symbol='*'))
        o = r2g(r)
        assert isinstance(o, dc.Point) and o.style == 'square'

    def test_text(self):
        r = regions.TextPixelRegion(center=regions.PixCoord(x=42, y=43),
                                    text='Foo',
                                    visual=regions.RegionVisual(textangle='45'))
        o = r2g(r)
        assert isinstance(o, dc.Text) and o.text == 'Foo'
        assert np.all(np.isclose((o.x, o.y, o.rot_deg),
                                 (r.center.x, r.center.y, float(r.visual['textangle']))))

    def test_line(self):
        r = regions.LinePixelRegion(start=regions.PixCoord(x=42, y=43),
                                    end=regions.PixCoord(x=42, y=43))
        o = r2g(r)
        assert isinstance(o, dc.Line)
        assert np.all(np.isclose((o.x1, o.y1, o.x2, o.y2),
                                 (r.start.x, r.start.y, r.end.x, r.end.y)))

    def test_rectangle(self):
        r = regions.RectanglePixelRegion(center=regions.PixCoord(x=42, y=43),
                                         width=3, height=4,
                                         angle=5 * u.deg)
        o = r2g(r)
        assert isinstance(o, dc.Box)
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.rot_deg),
                                 (r.center.x, r.center.y, r.width / 2.0, r.height / 2.0,
                                  r.angle.to(u.deg).value)))

    def test_circle(self):
        r = regions.CirclePixelRegion(center=regions.PixCoord(x=42, y=43),
                                      radius=4.2)
        o = r2g(r)
        assert isinstance(o, dc.Circle)
        assert np.all(np.isclose((o.x, o.y, o.radius), (r.center.x, r.center.y, r.radius)))

    def test_ellipse(self):
        r = regions.EllipsePixelRegion(center=regions.PixCoord(x=42, y=43),
                                       height=4.2, width=4.2, angle=5 * u.deg)
        o = r2g(r)
        assert isinstance(o, dc.Ellipse)
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.rot_deg),
                                 (r.center.x, r.center.y, r.width / 2., r.height / 2.,
                                  r.angle.to(u.deg).value)))

    def test_polygon(self):
        r = regions.PolygonPixelRegion(vertices=regions.PixCoord(x=[1, 2, 2], y=[1, 1, 2]))
        o = r2g(r)
        assert isinstance(o, dc.Polygon)
        assert np.all(np.isclose(o.points, np.array(r.vertices.xy).T))

    def test_circle_annulus(self):
        r = regions.CircleAnnulusPixelRegion(center=regions.PixCoord(x=42, y=43),
                                             inner_radius=4.2, outer_radius=5.2)
        o = r2g(r)
        assert isinstance(o, dc.Annulus)
        assert np.all(np.isclose((o.x, o.y, o.radius, o.radius + o.width),
                                 (r.center.x, r.center.y, r.inner_radius, r.outer_radius)))

    def test_ellipse_annulus(self):
        r = regions.EllipseAnnulusPixelRegion(center=regions.PixCoord(x=42, y=43),
                                              inner_width=4.2, outer_width=5.2,
                                              inner_height=7.2, outer_height=8.2,
                                              angle=5 * u.deg)
        o = r2g(r)
        assert isinstance(o, dc.Annulus2R) and o.atype == 'ellipse'
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.xradius + o.xwidth,
                                  o.yradius + o.ywidth, o.rot_deg),
                                 (r.center.x, r.center.y, r.inner_width / 2., r.inner_height / 2.,
                                  r.outer_width / 2., r.outer_height / 2.,
                                  r.angle.to(u.deg).value)))

    def test_rectangle_annulus(self):
        r = regions.RectangleAnnulusPixelRegion(center=regions.PixCoord(x=42, y=43),
                                                inner_width=4.2, outer_width=5.2,
                                                inner_height=7.2, outer_height=8.2,
                                                angle=5 * u.deg)
        o = r2g(r)
        assert isinstance(o, dc.Annulus2R) and o.atype == 'box'
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.xradius + o.xwidth,
                                  o.yradius + o.ywidth, o.rot_deg),
                                 (r.center.x, r.center.y, r.inner_width / 2., r.inner_height / 2.,
                                  r.outer_width / 2., r.outer_height / 2.,
                                  r.angle.to(u.deg).value)))


class Test_G2R(object):
    """Test conversions from Ginga canvas types to AstroPy regions."""

    def test_point1(self):
        o = dc.Point(42, 43, radius=5, style='cross')
        r = g2r(o)
        assert isinstance(r, regions.PointPixelRegion)
        assert np.all(np.isclose((o.x, o.y), (r.center.x, r.center.y)))
        assert r.visual['symbol'] == 'x'

    def test_point2(self):
        o = dc.Point(42, 43, radius=5, style='plus')
        r = g2r(o)
        assert isinstance(r, regions.PointPixelRegion)
        assert r.visual['symbol'] == '+'

    def test_point3(self):
        o = dc.Point(42, 43, radius=5, style='square')
        r = g2r(o)
        assert isinstance(r, regions.PointPixelRegion)
        assert r.visual['symbol'] == '*'

    def test_text(self):
        o = dc.Text(42, 43, text='Foo', rot_deg=45.0)
        r = g2r(o)
        assert isinstance(r, regions.TextPixelRegion) and r.text == 'Foo'
        assert np.all(np.isclose((o.x, o.y, o.rot_deg),
                                 (r.center.x, r.center.y, float(r.visual['textangle']))))

    def test_line(self):
        o = dc.Line(42, 43, 52, 53)
        r = g2r(o)
        assert isinstance(r, regions.LinePixelRegion)
        assert np.all(np.isclose((o.x1, o.y1, o.x2, o.y2),
                                 (r.start.x, r.start.y, r.end.x, r.end.y)))

    def test_box(self):
        o = dc.Box(42, 43, 10, 10)
        r = g2r(o)
        assert isinstance(r, regions.RectanglePixelRegion)
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius),
                                 (r.center.x, r.center.y, r.width / 2.0, r.height / 2.0)))

    def test_circle(self):
        o = dc.Circle(42, 43, 4.2)
        r = g2r(o)
        assert isinstance(r, regions.CirclePixelRegion)
        assert np.all(np.isclose((o.x, o.y, o.radius), (r.center.x, r.center.y, r.radius)))

    def test_ellipse(self):
        o = dc.Ellipse(42, 43, 4.2, 4.2, rot_deg=5.0)
        r = g2r(o)
        assert isinstance(r, regions.EllipsePixelRegion)
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.rot_deg),
                                 (r.center.x, r.center.y, r.width / 2., r.height / 2.,
                                  r.angle.to(u.deg).value)))

    def test_polygon(self):
        o = dc.Polygon([(1, 1), (2, 1), (2, 2)])
        r = g2r(o)
        assert isinstance(r, regions.PolygonPixelRegion)
        assert np.all(np.isclose(o.points, np.array(r.vertices.xy).T))

    def test_circle_annulus(self):
        o = dc.Annulus(42, 43, 4.2, width=1, atype='circle')
        r = g2r(o)
        assert isinstance(r, regions.CircleAnnulusPixelRegion)
        assert np.all(np.isclose((o.x, o.y, o.radius, o.radius + o.width),
                                 (r.center.x, r.center.y, r.inner_radius, r.outer_radius)))

    def test_ellipse_annulus(self):
        o = dc.Annulus2R(42, 43, 4.2, 7.2, xwidth=1, ywidth=1, rot_deg=5.0, atype='ellipse')
        r = g2r(o)
        assert isinstance(r, regions.EllipseAnnulusPixelRegion)
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.xradius + o.xwidth,
                                  o.yradius + o.ywidth, o.rot_deg),
                                 (r.center.x, r.center.y, r.inner_width / 2., r.inner_height / 2.,
                                  r.outer_width / 2., r.outer_height / 2.,
                                  r.angle.to(u.deg).value)))

    def test_rectangle_annulus(self):
        o = dc.Annulus2R(42, 43, 4.2, 7.2, xwidth=1, ywidth=1, rot_deg=5.0, atype='box')
        r = g2r(o)
        assert isinstance(r, regions.RectangleAnnulusPixelRegion)
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.xradius + o.xwidth,
                                  o.yradius + o.ywidth, o.rot_deg),
                                 (r.center.x, r.center.y, r.inner_width / 2., r.inner_height / 2.,
                                  r.outer_width / 2., r.outer_height / 2.,
                                  r.angle.to(u.deg).value)))
