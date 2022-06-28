"""Test ap_regions.py"""

import numpy as np
import pytest
import logging

regions = pytest.importorskip('regions')

from astropy import units as u
from astropy.coordinates import SkyCoord

from ginga.util.ap_region import (astropy_region_to_ginga_canvas_object as r2g,
                                  ginga_canvas_object_to_astropy_region as g2r)
from ginga.canvas.CanvasObject import get_canvas_types


dc = get_canvas_types()


class Test_R2G(object):
    """Test conversions from astropy-regions to Ginga canvas types."""

    def test_point_pix1(self):
        r = regions.PointPixelRegion(center=regions.PixCoord(x=42, y=43),
                                     visual=regions.RegionVisual(symbol='x'))
        o = r2g(r)
        assert isinstance(o, dc.Point) and o.style == 'cross'
        assert np.all(np.isclose((o.x, o.y), (r.center.x, r.center.y)))

    def test_point_pix2(self):
        r = regions.PointPixelRegion(center=regions.PixCoord(x=42, y=43),
                                     visual=regions.RegionVisual(symbol='+'))
        o = r2g(r)
        assert isinstance(o, dc.Point) and o.style == 'plus'

    def test_point_pix3(self):
        r = regions.PointPixelRegion(center=regions.PixCoord(x=42, y=43),
                                     visual=regions.RegionVisual(symbol='*'))
        o = r2g(r)
        assert isinstance(o, dc.Point) and o.style == 'square' and \
            o.coord == 'data'

    def test_point_sky1(self):
        r = regions.PointSkyRegion(center=SkyCoord(12.0, 10.0, unit='deg',
                                                   frame='fk5'),
                                   visual=regions.RegionVisual(symbol='*'))
        o = r2g(r)
        assert isinstance(o, dc.Point) and o.style == 'square' and \
            o.coord == 'wcs'

    def test_text_pix1(self):
        r = regions.TextPixelRegion(center=regions.PixCoord(x=42, y=43),
                                    text='Foo',
                                    visual=regions.RegionVisual(textangle='45'))
        o = r2g(r)
        assert isinstance(o, dc.Text) and o.text == 'Foo' and o.coord == 'data'
        assert np.all(np.isclose((o.x, o.y, o.rot_deg),
                                 (r.center.x, r.center.y, float(r.visual['textangle']))))

    def test_text_sky1(self):
        r = regions.TextSkyRegion(center=SkyCoord(12.0, 10.0, unit='deg',
                                                  frame='fk5'),
                                  text='Bar',
                                  visual=regions.RegionVisual(textangle='-50'))
        o = r2g(r)
        assert isinstance(o, dc.Text) and o.text == 'Bar' and o.coord == 'wcs'
        assert np.all(np.isclose((o.x, o.y, o.rot_deg),
                                 (r.center.ra.deg, r.center.dec.deg,
                                  float(r.visual['textangle']))))

    def test_line_pix1(self):
        r = regions.LinePixelRegion(start=regions.PixCoord(x=42, y=43),
                                    end=regions.PixCoord(x=42, y=43))
        o = r2g(r)
        assert isinstance(o, dc.Line) and o.coord == 'data'
        assert np.all(np.isclose((o.x1, o.y1, o.x2, o.y2),
                                 (r.start.x, r.start.y, r.end.x, r.end.y)))

    def test_line_sky1(self):
        r = regions.LineSkyRegion(start=SkyCoord(12.0, 10.0, unit='deg',
                                                 frame='fk5'),
                                  end=SkyCoord(12.5, 9.3, unit='deg',
                                               frame='fk5'))
        o = r2g(r)
        assert isinstance(o, dc.Line) and o.coord == 'wcs'
        assert np.all(np.isclose((o.x1, o.y1, o.x2, o.y2),
                                 (r.start.ra.deg, r.start.dec.deg,
                                  r.end.ra.deg, r.end.dec.deg)))

    def test_rectangle_pix1(self):
        r = regions.RectanglePixelRegion(center=regions.PixCoord(x=42, y=43),
                                         width=3, height=4,
                                         angle=5 * u.deg)
        o = r2g(r)
        assert isinstance(o, dc.Box)
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.rot_deg),
                                 (r.center.x, r.center.y, r.width * 0.5, r.height * 0.5,
                                  r.angle.to(u.deg).value)))

    def test_rectangle_sky1(self):
        r = regions.RectangleSkyRegion(center=SkyCoord(12.0, 10.0, unit='deg',
                                                       frame='fk5'),
                                       width=0.2 * u.deg, height=0.4 * u.deg,
                                       angle=5 * u.deg)
        o = r2g(r)
        assert isinstance(o, dc.Box) and o.coord == 'wcs'
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.rot_deg),
                                 (r.center.ra.deg, r.center.dec.deg,
                                  r.width.value * 0.5,
                                  r.height.value * 0.5,
                                  r.angle.to(u.deg).value)))

    def test_circle_pix1(self):
        r = regions.CirclePixelRegion(center=regions.PixCoord(x=42, y=43),
                                      radius=4.2)
        o = r2g(r)
        assert isinstance(o, dc.Circle)
        assert np.all(np.isclose((o.x, o.y, o.radius), (r.center.x, r.center.y, r.radius)))

    def test_circle_sky1(self):
        r = regions.CircleSkyRegion(center=SkyCoord(12.0, 10.0, unit='deg',
                                                    frame='fk5'),
                                    radius=0.5 * u.deg)
        o = r2g(r)
        assert isinstance(o, dc.Circle) and o.coord == 'wcs'
        assert np.all(np.isclose((o.x, o.y, o.radius),
                                 (r.center.ra.deg, r.center.dec.deg,
                                  r.radius.value)))

        # round-trip test
        r2 = g2r(o)
        assert isinstance(r2, regions.CircleSkyRegion)
        assert np.all(np.isclose((r.center.ra.deg, r.center.dec.deg, r.radius.value),
                                 (r2.center.ra.deg, r2.center.dec.deg, r2.radius.value)))

    def test_ellipse_pix1(self):
        r = regions.EllipsePixelRegion(center=regions.PixCoord(x=42, y=43),
                                       height=4.2, width=4.2, angle=5 * u.deg)
        o = r2g(r)
        assert isinstance(o, dc.Ellipse)
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.rot_deg),
                                 (r.center.x, r.center.y, r.width * 0.5, r.height * 0.5,
                                  r.angle.to(u.deg).value)))

    def test_ellipse_sky1(self):
        r = regions.EllipseSkyRegion(center=SkyCoord(12.0, 10.0, unit='deg',
                                                     frame='fk5'),
                                     height=0.4 * u.deg, width=0.2 * u.deg,
                                     angle=5 * u.deg)
        o = r2g(r)
        assert isinstance(o, dc.Ellipse) and o.coord == 'wcs'
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.rot_deg),
                                 (r.center.ra.deg, r.center.dec.deg,
                                  r.width.value * 0.5, r.height.value * 0.5,
                                  r.angle.to(u.deg).value)))

    def test_polygon_pix1(self):
        r = regions.PolygonPixelRegion(vertices=regions.PixCoord(x=[1, 2, 2], y=[1, 1, 2]))
        o = r2g(r)
        assert isinstance(o, dc.Polygon)
        assert np.all(np.isclose(o.points, np.array(r.vertices.xy).T))

    def test_polygon_sky1(self):
        r = regions.PolygonSkyRegion(vertices=SkyCoord([1, 2, 2], [1, 1, 2],
                                                       unit='deg', frame='fk5'))
        o = r2g(r)
        assert isinstance(o, dc.Polygon) and o.coord == 'wcs'
        vertices = np.array((r.vertices.ra.deg, r.vertices.dec.deg)).T
        assert np.all(np.isclose(o.points, vertices))

    def test_circle_annulus_pix1(self):
        r = regions.CircleAnnulusPixelRegion(center=regions.PixCoord(x=42, y=43),
                                             inner_radius=4.2, outer_radius=5.2)
        o = r2g(r)
        assert isinstance(o, dc.Annulus)
        assert np.all(np.isclose((o.x, o.y, o.radius, o.radius + o.width),
                                 (r.center.x, r.center.y, r.inner_radius, r.outer_radius)))

    def test_circle_annulus_sky1(self):
        r = regions.CircleAnnulusSkyRegion(center=SkyCoord(12.0, 10.0, unit='deg',
                                                           frame='fk5'),
                                           inner_radius=0.2 * u.deg,
                                           outer_radius=0.22 * u.deg)
        o = r2g(r)
        assert isinstance(o, dc.Annulus) and o.coord == 'wcs'
        assert np.all(np.isclose((o.x, o.y, o.radius, o.radius + o.width),
                                 (r.center.ra.deg, r.center.dec.deg,
                                  r.inner_radius.value, r.outer_radius.value)))

    def test_ellipse_annulus_pix1(self):
        r = regions.EllipseAnnulusPixelRegion(center=regions.PixCoord(x=42, y=43),
                                              inner_width=4.2, outer_width=5.2,
                                              inner_height=7.2, outer_height=8.2,
                                              angle=5 * u.deg)
        o = r2g(r)
        assert isinstance(o, dc.Annulus2R) and o.atype == 'ellipse'
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius,
                                  o.xradius + o.xwidth,
                                  o.yradius + o.ywidth, o.rot_deg),
                                 (r.center.x, r.center.y,
                                  r.inner_width * 0.5, r.inner_height * 0.5,
                                  r.outer_width * 0.5, r.outer_height * 0.5,
                                  r.angle.to(u.deg).value)))

    def test_ellipse_annulus_sky1(self):
        r = regions.EllipseAnnulusSkyRegion(center=SkyCoord(12.0, 10.0,
                                                            unit='deg',
                                                            frame='fk5'),
                                            inner_width=0.2 * u.deg,
                                            outer_width=0.4 * u.deg,
                                            inner_height=0.5 * u.deg,
                                            outer_height=0.6 * u.deg,
                                            angle=5 * u.deg)
        o = r2g(r)
        assert isinstance(o, dc.Annulus2R) and o.atype == 'ellipse' \
            and o.coord == 'wcs'
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius,
                                  o.xradius + o.xwidth,
                                  o.yradius + o.ywidth, o.rot_deg),
                                 (r.center.ra.deg, r.center.dec.deg,
                                  r.inner_width.value * 0.5,
                                  r.inner_height.value * 0.5,
                                  r.outer_width.value * 0.5,
                                  r.outer_height.value * 0.5,
                                  r.angle.to(u.deg).value)))

    def test_rectangle_annulus_pix1(self):
        r = regions.RectangleAnnulusPixelRegion(center=regions.PixCoord(x=42, y=43),
                                                inner_width=4.2,
                                                outer_width=5.2,
                                                inner_height=7.2,
                                                outer_height=8.2,
                                                angle=5 * u.deg)
        o = r2g(r)
        assert isinstance(o, dc.Annulus2R) and o.atype == 'box'
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.xradius + o.xwidth,
                                  o.yradius + o.ywidth, o.rot_deg),
                                 (r.center.x, r.center.y, r.inner_width * 0.5, r.inner_height * 0.5,
                                  r.outer_width * 0.5, r.outer_height * 0.5,
                                  r.angle.to(u.deg).value)))

    def test_rectangle_annulus_sky1(self):
        r = regions.RectangleAnnulusSkyRegion(center=SkyCoord(12.0, 10.0,
                                                              unit='deg',
                                                              frame='fk5'),
                                              inner_width=0.2 * u.deg,
                                              outer_width=0.4 * u.deg,
                                              inner_height=0.5 * u.deg,
                                              outer_height=0.6 * u.deg,
                                              angle=5 * u.deg)
        o = r2g(r)
        assert isinstance(o, dc.Annulus2R) and o.atype == 'box' and o.coord == 'wcs'
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.xradius + o.xwidth,
                                  o.yradius + o.ywidth, o.rot_deg),
                                 (r.center.ra.deg, r.center.dec.deg,
                                  r.inner_width.value * 0.5,
                                  r.inner_height.value * 0.5,
                                  r.outer_width.value * 0.5,
                                  r.outer_height.value * 0.5,
                                  r.angle.to(u.deg).value)))


class Test_G2R(object):
    """Test conversions from Ginga canvas types to astropy-regions Regions."""

    def test_point_pix1(self):
        o = dc.Point(42, 43, radius=5, style='cross')
        r = g2r(o)
        assert isinstance(r, regions.PointPixelRegion)
        assert np.all(np.isclose((o.x, o.y), (r.center.x, r.center.y)))
        assert r.visual['symbol'] == 'x'

    def test_point_pix2(self):
        o = dc.Point(42, 43, radius=5, style='plus')
        r = g2r(o)
        assert isinstance(r, regions.PointPixelRegion)
        assert r.visual['symbol'] == '+'

    def test_point_pix3(self):
        o = dc.Point(42, 43, radius=5, style='square')
        r = g2r(o)
        assert isinstance(r, regions.PointPixelRegion)
        assert r.visual['symbol'] == '*'

    def test_point_sky1(self):
        o = dc.Point(12.0, 10.0, radius=0.001, style='plus', coord='wcs')
        r = g2r(o)
        assert isinstance(r, regions.PointSkyRegion)
        assert r.visual['symbol'] == '+'
        assert np.all(np.isclose((o.x, o.y),
                                 (r.center.ra.deg, r.center.dec.deg)))

    def test_text_pix1(self):
        o = dc.Text(42, 43, text='Foo', rot_deg=45.0)
        r = g2r(o)
        assert isinstance(r, regions.TextPixelRegion) and r.text == 'Foo'
        assert np.all(np.isclose((o.x, o.y, o.rot_deg),
                                 (r.center.x, r.center.y, float(r.visual['textangle']))))

    def test_text_sky1(self):
        o = dc.Text(12.0, 10.0, text='Bar', rot_deg=45.0, coord='wcs')
        r = g2r(o)
        assert isinstance(r, regions.TextSkyRegion) and r.text == 'Bar'
        assert np.all(np.isclose((o.x, o.y, o.rot_deg),
                                 (r.center.ra.deg, r.center.dec.deg,
                                  float(r.visual['textangle']))))

    def test_line_pix1(self):
        o = dc.Line(42, 43, 52, 53, arrow='end', color='red')
        r = g2r(o)
        assert isinstance(r, regions.LinePixelRegion)
        assert r.visual['color'] == 'red'
        # lines ends (arrows) not supported yet, but from documentation
        # looks like they could be in the future?
        #assert r.visual['line'] == '[0 1]'
        assert np.all(np.isclose((o.x1, o.y1, o.x2, o.y2),
                                 (r.start.x, r.start.y, r.end.x, r.end.y)))

    def test_line_sky1(self):
        o = dc.Line(12.0, 10.0, 12.5, 9.3, color='blue', linewidth=2,
                    linestyle='dash', coord='wcs')
        r = g2r(o)
        assert isinstance(r, regions.LineSkyRegion)
        assert r.visual['color'] == 'blue'
        assert r.visual['linewidth'] == 2
        # ditto: dashed line
        #assert r.visual['dash'] == 1
        assert np.all(np.isclose((o.x1, o.y1, o.x2, o.y2),
                                 (r.start.ra.deg, r.start.dec.deg,
                                  r.end.ra.deg, r.end.dec.deg)))

    def test_box_pix1(self):
        o = dc.Box(42, 43, 10, 10)
        r = g2r(o)
        assert isinstance(r, regions.RectanglePixelRegion)
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius),
                                 (r.center.x, r.center.y, r.width * 0.5, r.height * 0.5)))

    def test_box_sky1(self):
        o = dc.Box(12.0, 10.0, 0.1, 0.2,
                   color='green', fill=True, fillcolor='orange', coord='wcs')
        r = g2r(o)
        assert isinstance(r, regions.RectangleSkyRegion)
        assert r.visual['color'] == 'green'
        assert r.visual['fill'] == 1
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius),
                                 (r.center.ra.deg, r.center.dec.deg,
                                  r.width.value * 0.5, r.height.value * 0.5)))

    def test_circle_pix1(self):
        o = dc.Circle(42, 43, 4.2)
        r = g2r(o)
        assert isinstance(r, regions.CirclePixelRegion)
        assert np.all(np.isclose((o.x, o.y, o.radius), (r.center.x, r.center.y, r.radius)))

    def test_circle_sky1(self):
        o = dc.Circle(12.0, 10.0, 1.1, coord='wcs')
        r = g2r(o)
        assert isinstance(r, regions.CircleSkyRegion)
        assert np.all(np.isclose((o.x, o.y, o.radius),
                                 (r.center.ra.deg, r.center.dec.deg, r.radius.value)))

    def test_ellipse_pix1(self):
        o = dc.Ellipse(42, 43, 4.2, 4.2, rot_deg=5.0)
        r = g2r(o)
        assert isinstance(r, regions.EllipsePixelRegion)
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.rot_deg),
                                 (r.center.x, r.center.y, r.width * 0.5, r.height * 0.5,
                                  r.angle.to(u.deg).value)))

    def test_ellipse_sky1(self):
        o = dc.Ellipse(12.0, 10.0, 0.2, 0.4, rot_deg=5.0, coord='wcs')
        r = g2r(o)
        assert isinstance(r, regions.EllipseSkyRegion)
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.rot_deg),
                                 (r.center.ra.deg, r.center.dec.deg,
                                  r.width.value * 0.5, r.height.value * 0.5,
                                  r.angle.to(u.deg).value)))

    def test_polygon_pix1(self):
        o = dc.Polygon([(1, 1), (2, 1), (2, 2)], color='red', fill=True,
                       linewidth=2)
        r = g2r(o)
        assert isinstance(r, regions.PolygonPixelRegion)
        assert np.all(np.isclose(o.points, np.array(r.vertices.xy).T))

        # round-trip test
        o2 = r2g(r)
        assert isinstance(o2, dc.Polygon) and o2.coord == 'data'
        assert o2.color == o2.color and o2.linewidth == o.linewidth and \
            o2.fill == o.fill
        assert np.all(np.isclose(o.points, o2.points))

    def test_polygon_sky1(self):
        o = dc.Polygon([(1, 1), (2, 1), (2, 2)], coord='wcs')
        r = g2r(o)
        assert isinstance(r, regions.PolygonSkyRegion)
        vertices = np.array((r.vertices.ra.deg, r.vertices.dec.deg)).T
        assert np.all(np.isclose(o.points, vertices))

    def test_circle_annulus_pix1(self):
        o = dc.Annulus(42, 43, 4.2, width=1, atype='circle')
        r = g2r(o)
        assert isinstance(r, regions.CircleAnnulusPixelRegion)
        assert np.all(np.isclose((o.x, o.y, o.radius, o.radius + o.width),
                                 (r.center.x, r.center.y, r.inner_radius, r.outer_radius)))

    def test_circle_annulus_sky1(self):
        o = dc.Annulus(12.0, 10.0, 1.0, width=0.01, atype='circle', coord='wcs')
        r = g2r(o)
        assert isinstance(r, regions.CircleAnnulusSkyRegion)
        assert np.all(np.isclose((o.x, o.y, o.radius, o.radius + o.width),
                                 (r.center.ra.deg, r.center.dec.deg,
                                  r.inner_radius.value, r.outer_radius.value)))

    def test_ellipse_annulus_pix1(self):
        o = dc.Annulus2R(42, 43, 4.2, 7.2, xwidth=1, ywidth=1, rot_deg=5.0, atype='ellipse')
        r = g2r(o)
        assert isinstance(r, regions.EllipseAnnulusPixelRegion)
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.xradius + o.xwidth,
                                  o.yradius + o.ywidth, o.rot_deg),
                                 (r.center.x, r.center.y, r.inner_width * 0.5, r.inner_height * 0.5,
                                  r.outer_width * 0.5, r.outer_height * 0.5,
                                  r.angle.to(u.deg).value)))

    def test_ellipse_annulus_sky1(self):
        o = dc.Annulus2R(12.0, 10.0, 1.0, 1.1, xwidth=0.1, ywidth=0.2,
                         rot_deg=5.0, atype='ellipse', coord='wcs')
        r = g2r(o)
        assert isinstance(r, regions.EllipseAnnulusSkyRegion)
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.xradius + o.xwidth,
                                  o.yradius + o.ywidth, o.rot_deg),
                                 (r.center.ra.deg, r.center.dec.deg,
                                  r.inner_width.value * 0.5,
                                  r.inner_height.value * 0.5,
                                  r.outer_width.value * 0.5,
                                  r.outer_height.value * 0.5,
                                  r.angle.to(u.deg).value)))

    def test_rectangle_annulus_pix1(self):
        o = dc.Annulus2R(42, 43, 4.2, 7.2, xwidth=1, ywidth=1, rot_deg=5.0, atype='box')
        r = g2r(o)
        assert isinstance(r, regions.RectangleAnnulusPixelRegion)
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.xradius + o.xwidth,
                                  o.yradius + o.ywidth, o.rot_deg),
                                 (r.center.x, r.center.y, r.inner_width * 0.5, r.inner_height * 0.5,
                                  r.outer_width * 0.5, r.outer_height * 0.5,
                                  r.angle.to(u.deg).value)))

    def test_rectangle_annulus_sky1(self):
        o = dc.Annulus2R(12.0, 10.0, 1.0, 1.1, xwidth=0.1, ywidth=0.2,
                         rot_deg=5.0, atype='box', coord='wcs')
        r = g2r(o)
        assert isinstance(r, regions.RectangleAnnulusSkyRegion)
        assert np.all(np.isclose((o.x, o.y, o.xradius, o.yradius, o.xradius + o.xwidth,
                                  o.yradius + o.ywidth, o.rot_deg),
                                 (r.center.ra.deg, r.center.dec.deg,
                                  r.inner_width.value * 0.5,
                                  r.inner_height.value * 0.5,
                                  r.outer_width.value * 0.5,
                                  r.outer_height.value * 0.5,
                                  r.angle.to(u.deg).value)))

    def test_skip_error(self):
        logger = logging.getLogger("test_ap_regions")
        o = dc.Crosshair(0, 0)
        r = g2r(o, logger=logger)
        assert isinstance(r, regions.TextPixelRegion)
        assert np.all(np.isclose((o.x, o.y), (r.center.x, r.center.y)))
