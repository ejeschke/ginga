#
# astro.py -- classes for special astronomy shapes drawn on
#                   ginga canvases.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import absolute_import, division, print_function

import math
import numpy

from ginga.AstroImage import AstroImage
from ginga.canvas.CanvasObject import (CanvasObjectBase, _bool, _color,
                                       Point, MovePoint, ScalePoint,
                                       register_canvas_types, get_canvas_type,
                                       colors_plus_none)
from ginga.misc.ParamSet import Param
from ginga.util import wcs
from ginga.util.wcs import raDegToString, decDegToString

from .mixins import OnePointMixin, TwoPointMixin, OnePointOneRadiusMixin
from .layer import CompoundObject

__all__ = ['Ruler', 'Compass', 'Crosshair', 'AnnulusMixin', 'Annulus',
           'WCSAxes']


class Ruler(TwoPointMixin, CanvasObjectBase):
    """
    Draws a WCS ruler (like a right triangle) on a DrawingCanvas.
    Parameters are:
    x1, y1: 0-based coordinates of one end of the diagonal in the data space
    x2, y2: 0-based coordinates of the opposite end of the diagonal
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
            Param(name='x1', type=float, default=0.0, argpos=0,
                  description="First X coordinate of object"),
            Param(name='y1', type=float, default=0.0, argpos=1,
                  description="First Y coordinate of object"),
            Param(name='x2', type=float, default=0.0, argpos=2,
                  description="Second X coordinate of object"),
            Param(name='y2', type=float, default=0.0, argpos=3,
                  description="Second Y coordinate of object"),
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default: solid)"),
            Param(name='color',
                  valid=colors_plus_none, type=_color, default='lightgreen',
                  description="Color of outline"),
            Param(name='showplumb', type=_bool,
                  default=True, valid=[False, True],
                  description="Show plumb lines for the ruler"),
            Param(name='color2',
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Second color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='units', type=str, default='arcmin',
                  valid=['arcmin', 'degrees', 'pixels'],
                  description="Units for text distance (default: arcmin)"),
            Param(name='font', type=str, default='Sans Serif',
                  description="Font family for text"),
            Param(name='fontsize', type=int, default=None,
                  min=8, max=72,
                  description="Font size of text (default: vary by scale)"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            ]

    @classmethod
    def idraw(cls, canvas, cxt):
        return cls(cxt.start_x, cxt.start_y, cxt.x, cxt.y, **cxt.drawparams)

    def __init__(self, x1, y1, x2, y2, color='green', color2='yellow',
                 alpha=1.0, linewidth=1, linestyle='solid',
                 showcap=True, showplumb=True, units='arcmin',
                 font='Sans Serif', fontsize=None, **kwdargs):
        self.kind = 'ruler'
        CanvasObjectBase.__init__(self, color=color, color2=color2,
                                  alpha=alpha, units=units,
                                  showplumb=showplumb,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  x1=x1, y1=y1, x2=x2, y2=y2,
                                  font=font, fontsize=fontsize,
                                  **kwdargs)
        TwoPointMixin.__init__(self)

    def get_points(self):
        points = [(self.x1, self.y1), (self.x2, self.y2)]
        points = self.get_data_points(points=points)
        return points

    def select_contains(self, viewer, data_x, data_y):
        points = self.get_points()
        x1, y1 = points[0]
        x2, y2 = points[1]
        return self.within_line(viewer, data_x, data_y, x1, y1, x2, y2,
                                self.cap_radius)

    def get_ruler_distances(self, viewer):
        mode = self.units.lower()
        points = self.get_points()
        x1, y1 = points[0]
        x2, y2 = points[1]

        try:
            image = viewer.get_image()
            if mode in ('arcmin', 'degrees'):
                # Calculate RA and DEC for the three points
                # origination point
                ra_org, dec_org = image.pixtoradec(x1, y1)

                # destination point
                ra_dst, dec_dst = image.pixtoradec(x2, y2)

                # "heel" point making a right triangle
                ra_heel, dec_heel = image.pixtoradec(x2, y1)

                if mode == 'arcmin':
                    text_h = wcs.get_starsep_RaDecDeg(ra_org, dec_org,
                                                      ra_dst, dec_dst)
                    text_x = wcs.get_starsep_RaDecDeg(ra_org, dec_org,
                                                      ra_heel, dec_heel)
                    text_y = wcs.get_starsep_RaDecDeg(ra_heel, dec_heel,
                                                      ra_dst, dec_dst)
                else:
                    sep_h = wcs.deltaStarsRaDecDeg(ra_org, dec_org,
                                                   ra_dst, dec_dst)
                    text_h = ("%.8f" % sep_h)
                    sep_x = wcs.deltaStarsRaDecDeg(ra_org, dec_org,
                                                   ra_heel, dec_heel)
                    text_x = ("%.8f" % sep_x)
                    sep_y = wcs.deltaStarsRaDecDeg(ra_heel, dec_heel,
                                                   ra_dst, dec_dst)
                    text_y = ("%.8f" % sep_y)
            else:
                dx = abs(x2 - x1)
                dy = abs(y2 - y1)
                dh = math.sqrt(dx**2 + dy**2)
                text_x = ("%.3f" % dx)
                text_y = ("%.3f" % dy)
                text_h = ("%.3f" % dh)

        except Exception as e:
            text_h = 'BAD WCS'
            text_x = 'BAD WCS'
            text_y = 'BAD WCS'

        return (text_x, text_y, text_h)

    def draw(self, viewer):
        points = self.get_points()
        x1, y1 = points[0]
        x2, y2 = points[1]
        cx1, cy1 = self.canvascoords(viewer, x1, y1)
        cx2, cy2 = self.canvascoords(viewer, x2, y2)

        text_x, text_y, text_h = self.get_ruler_distances(viewer)

        cr = viewer.renderer.setup_cr(self)
        cr.set_font_from_shape(self)

        cr.draw_line(cx1, cy1, cx2, cy2)
        self.draw_arrowhead(cr, cx1, cy1, cx2, cy2)
        self.draw_arrowhead(cr, cx2, cy2, cx1, cy1)

        # calculate offsets and positions for drawing labels
        # try not to cover anything up
        xtwd, xtht = cr.text_extents(text_x)
        ytwd, ytht = cr.text_extents(text_y)
        htwd, htht = cr.text_extents(text_h)

        diag_xoffset = 0
        diag_yoffset = 0
        xplumb_yoffset = 0
        yplumb_xoffset = 0

        diag_yoffset = 14
        if abs(cy1 - cy2) < 5:
            show_angle = 0  # noqa
        elif cy1 < cy2:
            xplumb_yoffset = -4
        else:
            xplumb_yoffset = 14
            diag_yoffset = -4

        if abs(cx1 - cx2) < 5:
            diag_xoffset = -(4 + htwd)
            show_angle = 0  # noqa
        elif (cx1 < cx2):
            diag_xoffset = -(4 + htwd)
            yplumb_xoffset = 4
        else:
            diag_xoffset = 4
            yplumb_xoffset = -(4 + ytwd)

        xh = min(cx1, cx2)
        y = cy1 + xplumb_yoffset
        xh += (max(cx1, cx2) - xh) // 2
        yh = min(cy1, cy2)
        x = cx2 + yplumb_xoffset
        yh += (max(cy1, cy2) - yh) // 2

        xd = xh + diag_xoffset
        yd = yh + diag_yoffset
        cr.draw_text(xd, yd, text_h)

        if self.showplumb:
            if self.color2:
                alpha = getattr(self, 'alpha', 1.0)
                cr.set_line(self.color2, alpha=alpha, style='dash')

            # draw X plumb line
            cr.draw_line(cx1, cy1, cx2, cy1)

            # draw Y plumb line
            cr.draw_line(cx2, cy1, cx2, cy2)

            # draw X plum line label
            xh -= xtwd // 2
            cr.draw_text(xh, y, text_x)

            # draw Y plum line label
            cr.draw_text(x, yh, text_y)

        if self.showcap:
            self.draw_caps(cr, self.cap, ((cx2, cy1), ))


class Compass(OnePointOneRadiusMixin, CanvasObjectBase):
    """
    Draws a WCS compass on a DrawingCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    radius: radius of the compass arms, in data units
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data'],
            ##       description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of center of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of center of object"),
            Param(name='radius', type=float, default=1.0,  argpos=2,
                  min=0.0,
                  description="Radius of object"),
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default solid)"),
            Param(name='color',
                  valid=colors_plus_none, type=_color, default='skyblue',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='font', type=str, default='Sans Serif',
                  description="Font family for text"),
            Param(name='fontsize', type=int, default=None,
                  min=8, max=72,
                  description="Font size of text (default: vary by scale)"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            ]

    @classmethod
    def idraw(cls, canvas, cxt):
        radius = max(abs(cxt.start_x - cxt.x), abs(cxt.start_y - cxt.y))
        return cls(cxt.start_x, cxt.start_y, radius, **cxt.drawparams)

    def __init__(self, x, y, radius, color='skyblue',
                 linewidth=1, fontsize=None, font='Sans Serif',
                 alpha=1.0, linestyle='solid', showcap=True, **kwdargs):
        self.kind = 'compass'
        CanvasObjectBase.__init__(self, color=color, alpha=alpha,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  x=x, y=y, radius=radius,
                                  font=font, fontsize=fontsize,
                                  **kwdargs)
        OnePointOneRadiusMixin.__init__(self)

    def get_points(self):
        # TODO: this attribute will be deprecated--fix!
        viewer = self.viewer

        image = viewer.get_image()
        x, y, xn, yn, xe, ye = image.calc_compass_radius(self.x,
                                                         self.y,
                                                         self.radius)
        return [(x, y), (xn, yn), (xe, ye)]

    def get_edit_points(self, viewer):
        c_pt, n_pt, e_pt = self.get_points()
        return [MovePoint(*c_pt), ScalePoint(*n_pt), ScalePoint(*e_pt)]

    def set_edit_point(self, i, pt, detail):
        if i == 0:
            x, y = pt
            self.move_to(x, y)
        elif i in (1, 2):
            x, y = pt
            self.radius = max(abs(x - self.x), abs(y - self.y))
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def select_contains(self, viewer, data_x, data_y):
        xd, yd = self.crdmap.to_data(self.x, self.y)
        return self.within_radius(viewer, data_x, data_y, xd, yd,
                                  self.cap_radius)

    def draw(self, viewer):
        cr = viewer.renderer.setup_cr(self)
        cr.set_font_from_shape(self)

        try:
            (cx1, cy1), (cx2, cy2), (cx3, cy3) = self.get_cpoints(viewer)
        except ValueError:
            cr.draw_text(self.x, self.y, 'BAD WCS')
            return

        # draw North line and arrowhead
        cr.draw_line(cx1, cy1, cx2, cy2)
        self.draw_arrowhead(cr, cx1, cy1, cx2, cy2)

        # draw East line and arrowhead
        cr.draw_line(cx1, cy1, cx3, cy3)
        self.draw_arrowhead(cr, cx1, cy1, cx3, cy3)

        # draw "N" & "E"
        cx, cy = self.get_textpos(cr, 'N', cx1, cy1, cx2, cy2)
        cr.draw_text(cx, cy, 'N')
        cx, cy = self.get_textpos(cr, 'E', cx1, cy1, cx3, cy3)
        cr.draw_text(cx, cy, 'E')

        if self.showcap:
            self.draw_caps(cr, self.cap, ((cx1, cy1), ))

    def get_textpos(self, cr, text, cx1, cy1, cx2, cy2):
        htwd, htht = cr.text_extents(text)
        diag_xoffset = 0
        diag_yoffset = 0
        xplumb_yoffset = 0
        yplumb_xoffset = 0

        diag_yoffset = 14
        if abs(cy1 - cy2) < 5:
            pass
        elif cy1 < cy2:
            xplumb_yoffset = -4
        else:
            xplumb_yoffset = 14
            diag_yoffset = -4

        if abs(cx1 - cx2) < 5:
            diag_xoffset = -(4 + htwd)
        elif (cx1 < cx2):
            diag_xoffset = -(4 + htwd)
            yplumb_xoffset = 4
        else:
            diag_xoffset = 4
            yplumb_xoffset = -(4 + 0)

        xh = min(cx1, cx2)
        y = cy1 + xplumb_yoffset  # noqa
        xh += (max(cx1, cx2) - xh) // 2
        yh = min(cy1, cy2)
        x = cx2 + yplumb_xoffset  # noqa
        yh += (max(cy1, cy2) - yh) // 2

        xd = xh + diag_xoffset
        yd = yh + diag_yoffset
        return (xd, yd)


class Crosshair(OnePointMixin, CanvasObjectBase):
    """
    Draws a crosshair on a DrawingCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data'],
            ##       description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of center of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of center of object"),
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default solid)"),
            Param(name='color',
                  valid=colors_plus_none, type=_color, default='green',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='text', type=str, default=None,
                  description="Text annotation"),
            Param(name='textcolor',
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of text annotation"),
            Param(name='font', type=str, default='Sans Serif',
                  description="Font family for text"),
            Param(name='fontsize', type=int, default=None,
                  min=8, max=72,
                  description="Font size of text (default: vary by scale)"),
            Param(name='format', type=str, default='xy',
                  valid=['xy', 'value', 'coords'],
                  description="Format for text annotation (default: xy)"),
            ]

    @classmethod
    def idraw(cls, canvas, cxt):
        return cls(cxt.x, cxt.y, **cxt.drawparams)

    def __init__(self, x, y, color='green',
                 linewidth=1, alpha=1.0, linestyle='solid',
                 text=None, textcolor='yellow',
                 fontsize=None, font='Sans Serif', format='xy',
                 **kwdargs):
        self.kind = 'crosshair'
        CanvasObjectBase.__init__(self, color=color, alpha=alpha,
                                  linewidth=linewidth, linestyle=linestyle,
                                  text=text, textcolor=textcolor,
                                  fontsize=fontsize, font=font,
                                  x=x, y=y, format=format, **kwdargs)
        OnePointMixin.__init__(self)

    def select_contains(self, viewer, data_x, data_y):
        xd, yd = self.crdmap.to_data(self.x, self.y)
        return self.within_radius(viewer, data_x, data_y, xd, yd,
                                  self.cap_radius)

    def draw(self, viewer):
        wd, ht = viewer.get_window_size()
        cpoints = self.get_cpoints(viewer)
        (cx, cy) = cpoints[0]

        hx1, hx2 = 0, wd
        hy1 = hy2 = cy
        vy1, vy2 = 0, ht
        vx1 = vx2 = cx

        if self.text is None:
            if self.format == 'xy':
                text = "X:%f, Y:%f" % (self.x, self.y)

            else:
                image = viewer.get_image()
                # NOTE: x, y are assumed to be in data coordinates
                info = image.info_xy(self.x, self.y, viewer.get_settings())
                if self.format == 'coords':
                    text = "%s:%s, %s:%s" % (info.ra_lbl, info.ra_txt,
                                             info.dec_lbl, info.dec_txt)
                else:
                    text = "V: %f" % (info.value)
        else:
            text = self.text

        cr = viewer.renderer.setup_cr(self)
        cr.set_font_from_shape(self)

        # draw horizontal line
        cr.draw_line(hx1, hy1, hx2, hy2)

        # draw vertical line
        cr.draw_line(vx1, vy1, vx2, vy2)

        txtwd, txtht = cr.text_extents(text)
        cr.set_line(self.textcolor, alpha=self.alpha)
        cr.draw_text(cx+10, cy+4+txtht, text)


class AnnulusMixin(object):

    def contains(self, x, y):
        """Containment test."""
        obj1, obj2 = self.objects
        return obj2.contains(x, y) and numpy.logical_not(obj1.contains(x, y))

    def contains_arr(self, x_arr, y_arr):
        """Containment test on arrays."""
        obj1, obj2 = self.objects
        arg1 = obj2.contains_arr(x_arr, y_arr)
        arg2 = numpy.logical_not(obj1.contains_arr(x_arr, y_arr))
        return numpy.logical_and(arg1, arg2)

    def get_llur(self):
        """Bounded by outer object."""
        obj2 = self.objects[1]
        return obj2.get_llur()

    def select_contains(self, viewer, data_x, data_y):
        obj2 = self.objects[1]
        return obj2.select_contains(viewer, data_x, data_y)


class Annulus(AnnulusMixin, OnePointOneRadiusMixin, CompoundObject):
    """
    Special compound object to handle annulus shape that
    consists of two objects with the same centroid.

    Examples
    --------
    >>> tag = canvas.add(Annulus(100, 200, 10, width=5, atype='circle'))
    >>> obj = canvas.get_object_by_tag(tag)
    >>> arr_masked = image.cutout_shape(obj)

    """
    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of center of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of center of object"),
            Param(name='radius', type=float, default=1.0,  argpos=2,
                  min=0.0,
                  description="Inner radius of annulus"),
            Param(name='width', type=float, default=None,
                  min=0.0,
                  description="Width of annulus"),
            Param(name='atype', type=str, default='circle',
                  valid=['circle', 'squarebox'],
                  description="Type of annulus"),
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default solid)"),
            Param(name='color',
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            ]

    @classmethod
    def idraw(cls, canvas, cxt):
        radius = math.sqrt(abs(cxt.start_x - cxt.x)**2 +
                           abs(cxt.start_y - cxt.y)**2)
        return cls(cxt.start_x, cxt.start_y, radius,
                   **cxt.drawparams)

    def __init__(self, x, y, radius, width=None,
                 atype='circle', color='yellow',
                 linewidth=1, linestyle='solid', alpha=1.0,
                 **kwdargs):

        if width is None:
            # default width is 15% of radius
            width = 0.15 * radius
        oradius = radius + width

        if oradius < radius:
            raise ValueError('Outer boundary < inner boundary')

        coord = kwdargs.get('coord', None)

        klass = get_canvas_type(atype)
        obj1 = klass(x, y, radius, color=color,
                     linewidth=linewidth,
                     linestyle=linestyle, alpha=alpha,
                     coord=coord)
        obj1.editable = False

        obj2 = klass(x, y, oradius, color=color,
                     linewidth=linewidth,
                     linestyle=linestyle, alpha=alpha,
                     coord=coord)
        obj2.editable = False

        CompoundObject.__init__(self, obj1, obj2,
                                x=x, y=y, radius=radius,
                                width=width, color=color,
                                linewidth=linewidth, linestyle=linestyle,
                                alpha=alpha, **kwdargs)
        OnePointOneRadiusMixin.__init__(self)

        self.editable = True
        self.opaque = True
        self.kind = 'annulus'

    def get_edit_points(self, viewer):
        points = ((self.x, self.y),
                  self.crdmap.offset_pt((self.x, self.y),
                                        self.radius, 0),
                  self.crdmap.offset_pt((self.x, self.y),
                                        self.radius + self.width, 0),
                  )
        points = self.get_data_points(points=points)
        return [MovePoint(*points[0]),
                ScalePoint(*points[1]),
                Point(*points[2])]

    def setup_edit(self, detail):
        detail.center_pos = self.get_center_pt()
        detail.radius = self.radius
        detail.width = self.width

    def set_edit_point(self, i, pt, detail):
        if i == 0:
            # move control point
            x, y = pt
            self.move_to(x, y)
        else:
            if i == 1:
                scalef = self.calc_scale_from_pt(pt, detail)
                # inner obj radius control pt
                self.radius = detail.radius * scalef
            elif i == 2:
                scalef = self.calc_scale_from_pt(pt, detail)
                width = detail.width * scalef
                # outer obj radius control pt--calculate new width
                assert width > 0, ValueError("Must have a positive width")
                self.width = width
            else:
                raise ValueError("No point corresponding to index %d" % (i))

        self.sync_state()

    def sync_state(self):
        """Called to synchronize state (e.g. when parameters have changed).
        """
        oradius = self.radius + self.width
        if oradius < self.radius:
            raise ValueError('Outer boundary < inner boundary')

        d = dict(x=self.x, y=self.y, radius=self.radius, color=self.color,
                 linewidth=self.linewidth, linestyle=self.linestyle,
                 alpha=self.alpha)

        # update inner object
        self.objects[0].__dict__.update(d)

        # update outer object
        d['radius'] = oradius
        self.objects[1].__dict__.update(d)

    def move_to(self, xdst, ydst):
        super(Annulus, self).move_to(xdst, ydst)

        self.set_data_points([(xdst, ydst)])


class WCSAxes(CompoundObject):
    """
    Special compound object to draw WCS axes.
    """
    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='dash',
                  valid=['solid', 'dash'],
                  description="Style of outline (default dash)"),
            Param(name='color',
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of grid and text"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of grid and text"),
            Param(name='font', type=str, default='Sans Serif',
                  description="Font family for text"),
            Param(name='fontsize', type=int, default=8,
                  min=8, max=72,
                  description="Font size of text (default: 8)"),
            ]

    def __init__(self, color='cyan',
                 linewidth=1, linestyle='dash', alpha=1.0,
                 font='Sans Serif', fontsize=8,
                 **kwdargs):

        # these could become supplied optional parameters, if desired
        self.show_label = True
        self.num_ra = 10
        self.num_dec = 10
        self._pix_res = 10
        self.txt_off = 4
        self.ra_angle = None
        self.dec_angle = None
        # for keeping track of changes to image and orientation
        self._cur_rot = None
        self._cur_swap = None
        self._cur_image = None

        CompoundObject.__init__(self,
                                color=color, alpha=alpha,
                                linewidth=linewidth, linestyle=linestyle,
                                font=font, fontsize=fontsize, **kwdargs)

        self.editable = False
        self.pickable = False
        self.opaque = True
        self.kind = 'wcsaxes'

    def _calc_axes(self, viewer, image, rot_deg, swapxy):
        self._cur_image = image
        self._cur_rot = rot_deg
        self._cur_swap = swapxy

        if not isinstance(image, AstroImage) or not image.has_valid_wcs():
            return []

        # Approximate bounding box in RA/DEC space
        xmax = image.width - 1
        ymax = image.height - 1
        try:
            radec = image.wcs.datapt_to_coords(
                [[0, 0], [0, ymax], [xmax, 0], [xmax, ymax]],
                naxispath=image.naxispath)
        except Exception:
            return []
        ra_min, dec_min = radec.ra.min().deg, radec.dec.min().deg
        ra_max, dec_max = radec.ra.max().deg, radec.dec.max().deg
        ra_size = ra_max - ra_min
        dec_size = dec_max - dec_min

        # Calculate positions of RA/DEC lines
        d_ra = ra_size / (self.num_ra + 1)
        d_dec = dec_size / (self.num_dec + 1)
        ra_arr = numpy.arange(ra_min + d_ra, ra_max - d_ra * 0.5, d_ra)
        dec_arr = numpy.arange(dec_min + d_dec, dec_max - d_ra * 0.5, d_dec)

        # RA/DEC step size for each vector
        min_imsize = min(image.width, image.height)
        d_ra_step = ra_size * self._pix_res / min_imsize
        d_dec_step = dec_size * self._pix_res / min_imsize

        # Create Path objects
        objs = []

        for cur_ra in ra_arr:
            crds = [[cur_ra, cur_dec] for cur_dec in
                    numpy.arange(dec_min, dec_max + d_dec_step, d_dec_step)]
            lbl = raDegToString(cur_ra)
            objs += self._get_path(viewer, image, crds, lbl, 1)
        for cur_dec in dec_arr:
            crds = [[cur_ra, cur_dec] for cur_ra in
                    numpy.arange(ra_min, ra_max + d_ra_step, d_ra_step)]
            lbl = decDegToString(cur_dec)
            objs += self._get_path(viewer, image, crds, lbl, 0)

        return objs

    def _get_path(self, viewer, image, crds, lbl, axis):
        from ginga.canvas.types.basic import Path, Text

        try:
            pts = image.wcs.wcspt_to_datapt(crds, naxispath=image.naxispath)
        except Exception:
            return []

        # Don't draw outside image area
        mask = ((pts[:, 0] >= 0) & (pts[:, 0] < image.width) &
                (pts[:, 1] >= 0) & (pts[:, 1] < image.height))
        pts = pts[mask]

        path_obj = Path(
            points=pts, coords='data', linewidth=self.linewidth,
            linestyle=self.linestyle, color=self.color,
            alpha=self.alpha)
        # this is necessary because we are not actually adding to a canvas
        path_obj.crdmap = viewer.get_coordmap('data')

        if self.show_label:
            # Calculate label orientation
            x1, y1 = pts[0]
            x2, y2 = pts[-1]
            dx = x2 - x1
            dy = y2 - y1
            m = dy / dx
            c = y1 - m * x1

            if abs(m) < 1:  # x axis varying
                x = min(x1, x2) + abs(dx) * 0.45
                y = m * x + c + self.txt_off
            else:  # y axis varying
                y = min(y1, y2) + abs(dy) * 0.45
                if numpy.isfinite(m):
                    x = (y - c) / m
                else:
                    x = min(x1, x2)
                x += self.txt_off

            if axis == 0:  # DEC
                user_angle = self.dec_angle
                default_rot = 0
            else:  # RA
                user_angle = self.ra_angle
                default_rot = 90

            if user_angle is None:
                try:
                    rot = math.atan(m) * 180 / math.pi
                except ValueError:
                    rot = default_rot
                rot = self._cur_rot + rot
            else:
                rot = user_angle

            if self._cur_swap:
                # axes are swapped
                rot -= 90

            text_obj = Text(x, y, text=lbl, font=self.font,
                            fontsize=self.fontsize, color=self.color,
                            alpha=self.alpha, rot_deg=rot, coord='data')
            text_obj.crdaxis = axis
            # this is necessary because we are not actually adding to a canvas
            text_obj.crdmap = viewer.get_coordmap('data')

            return [path_obj, text_obj]

        else:
            return [path_obj]

    def sync_state(self):
        for obj in self.objects:
            if obj.kind == 'text':
                if self.show_label:
                    obj.alpha = self.alpha
                    obj.color = self.color
                    obj.font = self.font
                    obj.fontsize = self.fontsize
                    if obj.crdaxis == 0 and self.dec_angle is not None:
                        obj.rot_deg = self.dec_angle
                    elif obj.crdaxis == 1 and self.ra_angle is not None:
                        obj.rot_deg = self.ra_angle
                else:
                    obj.alpha = 0  # hide

            else:  # path
                obj.alpha = self.alpha
                obj.color = self.color
                obj.linewidth = self.linewidth
                obj.linestyle = self.linestyle

    def draw(self, viewer):
        # see if we need to recalculate our grid
        image = viewer.get_image()
        update = False
        if self._cur_image != image:
            # new image loaded
            update = True

        cur_swap = viewer.get_transforms()[2]
        if cur_swap != self._cur_swap:
            # axes have been swapped
            update = True

        cur_rot = viewer.get_rotation()
        if cur_rot != self._cur_rot and self.show_label:
            # rotation has changed
            # TODO: for a rotation or swap axes change, it would be
            # sufficient to simply calculate the new rotation angles
            # and update all the text objects in self.objects
            update = True

        if len(self.objects) == 0:
            # initial time
            update = True

        if update:
            # only expensive recalculation of grid if needed
            self.ra_angle = None
            self.dec_angle = None
            self.objects = self._calc_axes(viewer, image, cur_rot, cur_swap)

        super(WCSAxes, self).draw(viewer)


register_canvas_types(dict(ruler=Ruler, compass=Compass,
                           crosshair=Crosshair, annulus=Annulus,
                           wcsaxes=WCSAxes))

# END
