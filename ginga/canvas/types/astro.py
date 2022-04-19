#
# astro.py -- classes for special astronomy shapes drawn on
#                   ginga canvases.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

import math
import numpy as np

from ginga.canvas.CanvasObject import (CanvasObjectBase, _bool, _color,
                                       Point, MovePoint, ScalePoint,
                                       register_canvas_types, get_canvas_type,
                                       colors_plus_none, coord_names)
from ginga.misc.ParamSet import Param
from ginga.misc import Bunch
from ginga.util import wcs
from ginga.util.wcs import ra_deg_to_str, dec_deg_to_str

from .mixins import (OnePointMixin, TwoPointMixin, OnePointOneRadiusMixin,
                     OnePointTwoRadiusMixin)
from .layer import CompoundObject

__all__ = ['Ruler', 'Compass', 'Crosshair', 'AnnulusMixin', 'Annulus',
           'Annulus2R', 'WCSAxes']


class RulerP(TwoPointMixin, CanvasObjectBase):
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
            Param(name='coord', type=str, default='data',
                  valid=coord_names,
                  description="Set type of coordinates"),
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
            Param(name='showends', type=_bool,
                  default=False, valid=[False, True],
                  description="Show begin and end values for the ruler"),
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
            Param(name='fontsize', type=float, default=None,
                  min=8, max=72,
                  description="Font size of text (default: vary by scale)"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        return cls((cxt.start_x, cxt.start_y), (cxt.x, cxt.y), **cxt.drawparams)

    def __init__(self, pt1, pt2, color='green', color2='skyblue',
                 alpha=1.0, linewidth=1, linestyle='solid',
                 showcap=True, showplumb=True, showends=False, units='arcmin',
                 font='Sans Serif', fontsize=None, **kwdargs):
        self.kind = 'ruler'
        points = np.asarray([pt1, pt2], dtype=float)
        CanvasObjectBase.__init__(self, color=color, color2=color2,
                                  alpha=alpha, units=units,
                                  showplumb=showplumb, showends=showends,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle, points=points,
                                  font=font, fontsize=fontsize,
                                  **kwdargs)
        TwoPointMixin.__init__(self)

    def get_points(self):
        points = [(self.x1, self.y1), (self.x2, self.y2)]
        points = self.get_data_points(points=points)
        return points

    def select_contains_pt(self, viewer, pt):
        points = self.get_points()
        return self.within_line(viewer, pt, points[0], points[1],
                                self.cap_radius)

    def get_arcmin(self, sep):
        sgn, deg, mn, sec = wcs.degToDms(sep)
        if deg != 0:
            txt = '%02d:%02d:%06.3f' % (deg, mn, sec)
        else:
            txt = '%02d:%06.3f' % (mn, sec)
        return txt

    def get_ruler_distances(self, viewer):
        mode = self.units.lower()
        points = self.get_data_points()
        x1, y1 = points[0]
        x2, y2 = points[1]

        text = Bunch.Bunch(dict().fromkeys(['x', 'y', 'h', 'b', 'e'],
                                           'BAD WCS'))
        try:
            image = viewer.get_image()
            res = wcs.get_ruler_distances(image, points[0], points[1])
            text.res = res

            if mode == 'arcmin':
                text.h = self.get_arcmin(res.dh_deg)
                text.x = self.get_arcmin(res.dx_deg)
                text.y = self.get_arcmin(res.dy_deg)
                text.b = ("%s, %s" % (wcs.ra_deg_to_str(res.ra_org),
                                      wcs.dec_deg_to_str(res.dec_org)))
                text.e = ("%s, %s" % (wcs.ra_deg_to_str(res.ra_dst),
                                      wcs.dec_deg_to_str(res.dec_dst)))

            elif mode == 'degrees':
                text.h = ("%.8f" % res.dh_deg)
                text.x = ("%.8f" % res.dx_deg)
                text.y = ("%.8f" % res.dy_deg)
                text.b = ("%.3f, %.3f" % (res.ra_org, res.dec_org))
                text.e = ("%.3f, %.3f" % (res.ra_dst, res.dec_dst))

            else:
                text.x = ("%.3f" % abs(res.dx_pix))
                text.y = ("%.3f" % abs(res.dy_pix))
                text.h = ("%.3f" % res.dh_pix)
                text.b = ("%.3f, %.3f" % (res.x1, res.y1))
                text.e = ("%.3f, %.3f" % (res.x2, res.y2))

        except Exception as e:
            print(str(e))
            pass

        return text

    def draw(self, viewer):
        points = self.get_points()
        x1, y1 = points[0]
        x2, y2 = points[1]
        cx1, cy1 = viewer.get_canvas_xy(x1, y1)
        cx2, cy2 = viewer.get_canvas_xy(x2, y2)

        text = self.get_ruler_distances(viewer)

        cr = viewer.renderer.setup_cr(self)
        cr.set_font_from_shape(self)

        cr.draw_line(cx1, cy1, cx2, cy2)
        self.draw_arrowhead(cr, cx1, cy1, cx2, cy2)
        self.draw_arrowhead(cr, cx2, cy2, cx1, cy1)

        # calculate offsets and positions for drawing labels
        # try not to cover anything up
        xtwd, xtht = cr.text_extents(text.x)
        ytwd, ytht = cr.text_extents(text.y)
        htwd, htht = cr.text_extents(text.h)

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
        cr.draw_text(xd, yd, text.h)

        if self.showends:
            cr.draw_text(cx1 + 4, cy1 + xtht + 4, text.b)
            cr.draw_text(cx2 + 4, cy2 + xtht + 4, text.e)

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
            cr.draw_text(xh, y, text.x)

            # draw Y plum line label
            cr.draw_text(x, yh, text.y)

        if self.showcap and self.showplumb:
            # only cap is at intersection of plumb lines
            self.draw_caps(cr, self.cap, ((cx2, cy1), ))


class Ruler(RulerP):

    @classmethod
    def idraw(cls, canvas, cxt):
        return cls(cxt.start_x, cxt.start_y, cxt.x, cxt.y, **cxt.drawparams)

    def __init__(self, x1, y1, x2, y2, color='green', color2='skyblue',
                 alpha=1.0, linewidth=1, linestyle='solid',
                 showcap=True, showplumb=True, showends=False, units='arcmin',
                 font='Sans Serif', fontsize=None, **kwdargs):
        RulerP.__init__(self, (x1, y1), (x2, y2), color=color, color2=color2,
                        alpha=alpha, units=units,
                        showplumb=showplumb, showends=showends,
                        linewidth=linewidth, showcap=showcap,
                        linestyle=linestyle, font=font, fontsize=fontsize,
                        **kwdargs)


class CompassP(OnePointOneRadiusMixin, CanvasObjectBase):
    """
    Draws a WCS compass on a DrawingCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the coordinate space
    radius: radius of the compass arms, in coordinate units
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='coord', type=str, default='data',
                  valid=coord_names,
                  description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of center of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of center of object"),
            Param(name='radius', type=float, default=1.0, argpos=2,
                  min=0.0,
                  description="Radius of object"),
            Param(name='ctype', type=str, default='wcs',
                  valid=['pixel', 'wcs'],
                  description="Type of compass (wcs (N/E), or pixel (X/Y))"),
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
            Param(name='fontsize', type=float, default=None,
                  min=8, max=72,
                  description="Font size of text (default: vary by scale)"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        radius = np.sqrt(abs(cxt.start_x - cxt.x) ** 2 +
                         abs(cxt.start_y - cxt.y) ** 2)
        return cls((cxt.start_x, cxt.start_y), radius, **cxt.drawparams)

    def __init__(self, pt, radius, ctype='wcs', color='skyblue',
                 linewidth=1, fontsize=None, font='Sans Serif',
                 alpha=1.0, linestyle='solid', showcap=True, **kwdargs):
        self.kind = 'compass'
        points = np.asarray([pt], dtype=float)
        CanvasObjectBase.__init__(self, ctype=ctype, color=color, alpha=alpha,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  points=points, radius=radius,
                                  font=font, fontsize=fontsize,
                                  **kwdargs)
        OnePointOneRadiusMixin.__init__(self)

    def get_edit_points(self, viewer):
        points = self.get_data_points(points=(
            (self.x, self.y),
            self.crdmap.offset_pt((self.x, self.y),
                                  (self.radius, self.radius)), ))
        x, y = points[0]
        x1, y1 = points[1]
        radius = math.sqrt((x1 - x) ** 2 + (y1 - y) ** 2)

        return [MovePoint(x, y),
                ScalePoint(x + radius, y + radius),
                ]

    def get_llur(self):
        points = self.get_data_points(points=(
            (self.x, self.y),
            self.crdmap.offset_pt((self.x, self.y),
                                  (self.radius, self.radius)), ))
        x, y = points[0]
        x1, y1 = points[1]
        radius = math.sqrt((x1 - x) ** 2 + (y1 - y) ** 2)

        x1, y1, x2, y2 = x - radius, y - radius, x + radius, y + radius
        return self.swapxy(x1, y1, x2, y2)

    def select_contains_pt(self, viewer, pt):
        p0 = self.crdmap.to_data((self.x, self.y))
        return self.within_radius(viewer, pt, p0, self.cap_radius)

    def draw(self, viewer):

        points = self.get_data_points(points=(
            (self.x, self.y),
            self.crdmap.offset_pt((self.x, self.y),
                                  (self.radius, self.radius)), ))
        x, y = points[0]
        x1, y1 = points[1]
        radius = math.sqrt((x1 - x) ** 2 + (y1 - y) ** 2)

        bad_arms = False

        if self.ctype == 'wcs':
            image = viewer.get_image()
            if image is None:
                return

            try:
                x, y, xn, yn, xe, ye = wcs.calc_compass_radius(image,
                                                               x, y,
                                                               radius)
            except Exception as e:
                bad_arms = True

        elif self.ctype == 'pixel':
            xn, yn, xe, ye = x, y + radius, x + radius, y

        cr = viewer.renderer.setup_cr(self)
        cr.set_font_from_shape(self)

        if bad_arms:
            points = self.get_cpoints(viewer, points=[(x, y)])
            cx, cy = points[0]
            cr.draw_text(cx, cy, 'BAD WCS')
            return

        points = np.asarray([(x, y), (xn, yn), (xe, ye)])

        (cx1, cy1), (cx2, cy2), (cx3, cy3) = self.get_cpoints(viewer,
                                                              points=points)
        # draw North line and arrowhead
        cr.draw_line(cx1, cy1, cx2, cy2)
        self.draw_arrowhead(cr, cx1, cy1, cx2, cy2)

        # draw East line and arrowhead
        cr.draw_line(cx1, cy1, cx3, cy3)
        self.draw_arrowhead(cr, cx1, cy1, cx3, cy3)

        # draw "N" & "E" or "X" and "Y"
        if self.ctype == 'pixel':
            te, tn = 'X', 'Y'
        else:
            te, tn = 'E', 'N'
        cx, cy = self.get_textpos(cr, tn, cx1, cy1, cx2, cy2)
        cr.draw_text(cx, cy, tn)
        cx, cy = self.get_textpos(cr, te, cx1, cy1, cx3, cy3)
        cr.draw_text(cx, cy, te)

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


class Compass(CompassP):

    @classmethod
    def idraw(cls, canvas, cxt):
        radius = np.sqrt(abs(cxt.start_x - cxt.x) ** 2 +
                         abs(cxt.start_y - cxt.y) ** 2)
        return cls(cxt.start_x, cxt.start_y, radius, **cxt.drawparams)

    def __init__(self, x, y, radius, ctype='wcs', color='skyblue',
                 linewidth=1, fontsize=None, font='Sans Serif',
                 alpha=1.0, linestyle='solid', showcap=True, **kwdargs):
        CompassP.__init__(self, (x, y), radius, ctype=ctype, color=color,
                          alpha=alpha, linewidth=linewidth, showcap=showcap,
                          linestyle=linestyle, font=font, fontsize=fontsize,
                          **kwdargs)


class CrosshairP(OnePointMixin, CanvasObjectBase):
    """
    Draws a crosshair on a DrawingCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='coord', type=str, default='data',
                  valid=coord_names,
                  description="Set type of coordinates"),
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
            Param(name='fontsize', type=float, default=None,
                  min=8, max=72,
                  description="Font size of text (default: vary by scale)"),
            Param(name='fontscale', type=_bool,
                  default=True, valid=[False, True],
                  description="Scale font with scale of viewer"),
            Param(name='format', type=str, default='xy',
                  valid=['xy', 'value', 'coords'],
                  description="Format for text annotation (default: xy)"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        return cls((cxt.x, cxt.y), **cxt.drawparams)

    def __init__(self, pt, color='green',
                 linewidth=1, alpha=1.0, linestyle='solid',
                 text=None, textcolor='yellow',
                 fontsize=10.0, font='Sans Serif', fontscale=True,
                 format='xy', **kwdargs):
        self.kind = 'crosshair'
        points = np.asarray([pt], dtype=float)
        CanvasObjectBase.__init__(self, color=color, alpha=alpha,
                                  linewidth=linewidth, linestyle=linestyle,
                                  text=text, textcolor=textcolor,
                                  fontsize=fontsize, font=font,
                                  fontscale=fontscale,
                                  points=points, format=format, **kwdargs)
        OnePointMixin.__init__(self)

        self.fontsize_min = 8.0
        self.fontsize_max = 14.0

    def select_contains_pt(self, viewer, pt):
        p0 = self.crdmap.to_data((self.x, self.y))
        return self.within_radius(viewer, pt, p0, self.cap_radius)

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
                image = viewer.get_vip()
                # NOTE: x, y are assumed to be in data coordinates
                info = image.info_xy(self.x, self.y, viewer.get_settings())
                if self.format == 'coords':
                    if 'ra_lbl' not in info:
                        text = 'No WCS'
                    else:
                        text = "%s:%s, %s:%s" % (info.ra_lbl, info.ra_txt,
                                                 info.dec_lbl, info.dec_txt)
                else:
                    if info.value is None:
                        text = "V: None"
                    elif np.isscalar(info.value) or len(info.value) <= 1:
                        text = "V: %f" % (info.value)
                    else:
                        values = ', '.join(["%d" % info.value[i]
                                           for i in range(len(info.value))])
                        text = "V: [%s]" % (str(values))
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
        cr.draw_text(cx + 10, cy + 4 + txtht, text)


class Crosshair(CrosshairP):

    @classmethod
    def idraw(cls, canvas, cxt):
        return cls(cxt.x, cxt.y, **cxt.drawparams)

    def __init__(self, x, y, color='green',
                 linewidth=1, alpha=1.0, linestyle='solid',
                 text=None, textcolor='yellow',
                 fontsize=10.0, font='Sans Serif', fontscale=True,
                 format='xy', **kwdargs):
        CrosshairP.__init__(self, (x, y), color=color, alpha=alpha,
                            linewidth=linewidth, linestyle=linestyle,
                            text=text, textcolor=textcolor,
                            fontsize=fontsize, font=font,
                            fontscale=fontscale,
                            format=format, **kwdargs)


class AnnulusMixin(object):

    def contains_pt(self, pt):
        """Containment test."""
        obj1, obj2 = self.objects
        return obj2.contains_pt(pt) and np.logical_not(obj1.contains_pt(pt))

    def contains_pts(self, pts):
        """Containment test on arrays."""
        obj1, obj2 = self.objects
        arg1 = obj2.contains_pts(pts)
        arg2 = np.logical_not(obj1.contains_pts(pts))
        return np.logical_and(arg1, arg2)

    def get_llur(self):
        """Bounded by outer object."""
        obj2 = self.objects[1]
        return obj2.get_llur()

    def select_contains_pt(self, viewer, pt):
        obj2 = self.objects[1]
        return obj2.select_contains_pt(viewer, pt)


class AnnulusP(AnnulusMixin, OnePointOneRadiusMixin, CompoundObject):
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
            Param(name='coord', type=str, default='data',
                  valid=coord_names,
                  description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of center of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of center of object"),
            Param(name='radius', type=float, default=1.0, argpos=2,
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
        radius = np.sqrt(abs(cxt.start_x - cxt.x)**2 +
                         abs(cxt.start_y - cxt.y)**2)
        return cls((cxt.start_x, cxt.start_y), radius,
                   **cxt.drawparams)

    def __init__(self, pt, radius, width=None,
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
        obj1 = klass(pt[0], pt[1], radius, color=color,
                     linewidth=linewidth,
                     linestyle=linestyle, alpha=alpha,
                     coord=coord)
        obj1.editable = False

        obj2 = klass(pt[0], pt[1], oradius, color=color,
                     linewidth=linewidth,
                     linestyle=linestyle, alpha=alpha,
                     coord=coord)
        obj2.editable = False

        points = np.asarray([pt], dtype=float)

        CompoundObject.__init__(self, obj1, obj2,
                                points=points, radius=radius,
                                width=width, color=color,
                                linewidth=linewidth, linestyle=linestyle,
                                alpha=alpha, **kwdargs)
        OnePointOneRadiusMixin.__init__(self)

        self.editable = True
        self.opaque = True
        self.atype = atype
        self.kind = 'annulus'

    def get_edit_points(self, viewer):
        points = ((self.x, self.y),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (self.radius, 0)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (self.radius + self.width, 0)),
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
            self.move_to_pt(pt)
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

        d = dict(points=self.points, radius=self.radius, color=self.color,
                 linewidth=self.linewidth, linestyle=self.linestyle,
                 alpha=self.alpha, coord=self.coord, crdmap=self.crdmap)

        # update inner object
        self.objects[0].__dict__.update(d)

        # update outer object
        d['radius'] = oradius
        self.objects[1].__dict__.update(d)

    def move_to_pt(self, dst_pt):
        super(AnnulusP, self).move_to_pt(dst_pt)

        self.set_data_points([dst_pt])


class Annulus(AnnulusP):

    @classmethod
    def idraw(cls, canvas, cxt):
        radius = np.sqrt(abs(cxt.start_x - cxt.x)**2 +
                         abs(cxt.start_y - cxt.y)**2)
        return cls(cxt.start_x, cxt.start_y, radius,
                   **cxt.drawparams)

    def __init__(self, x, y, radius, width=None,
                 atype='circle', color='yellow',
                 linewidth=1, linestyle='solid', alpha=1.0,
                 **kwdargs):
        AnnulusP.__init__(self, (x, y), radius, width=width, atype=atype,
                          color=color, linewidth=linewidth,
                          linestyle=linestyle, alpha=alpha, **kwdargs)


class Annulus2RP(AnnulusMixin, OnePointTwoRadiusMixin, CompoundObject):
    """
    Special compound object to handle annulus shape that
    consists of two objects, (one center point, plus two radii).

    Examples
    --------
    >>> tag = canvas.add(Annulus2R(100, 200, 10, 20, width=5, atype='box'))
    >>> obj = canvas.get_object_by_tag(tag)
    >>> arr_masked = image.cutout_shape(obj)

    """
    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='coord', type=str, default='data',
                  valid=coord_names,
                  description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of center of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of center of object"),
            Param(name='xradius', type=float, default=1.0, argpos=2,
                  min=0.0,
                  description="Inner X radius of annulus"),
            Param(name='yradius', type=float, default=1.0, argpos=2,
                  min=0.0,
                  description="Inner Y radius of annulus"),
            Param(name='xwidth', type=float, default=None,
                  min=0.0,
                  description="Width in X of annulus"),
            Param(name='ywidth', type=float, default=None,
                  min=0.0,
                  description="Width in Y of annulus"),
            Param(name='atype', type=str, default='ellipse',
                  valid=['ellipse', 'box'],
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
            Param(name='rot_deg', type=float, default=0.0,
                  min=-359.999, max=359.999, widget='spinfloat', incr=1.0,
                  description="Rotation about center of object"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        xradius, yradius = abs(cxt.start_x - cxt.x), abs(cxt.start_y - cxt.y)
        return cls((cxt.start_x, cxt.start_y), (xradius, yradius),
                   **cxt.drawparams)

    def __init__(self, pt, radii, xwidth=None,
                 ywidth=None, atype='ellipse', color='yellow',
                 linewidth=1, linestyle='solid', alpha=1.0,
                 rot_deg=0.0, **kwdargs):
        xradius, yradius = radii
        if xwidth is None:
            # default X width is 15% of X radius
            xwidth = 0.15 * xradius
        if ywidth is None:
            # default Y width is X width
            ywidth = xwidth
        oxradius = xradius + xwidth
        oyradius = yradius + ywidth

        if oxradius < xradius or oyradius < yradius:
            raise ValueError('Outer boundary < inner boundary')

        coord = kwdargs.get('coord', None)

        klass = get_canvas_type(atype)
        obj1 = klass(pt[0], pt[1], radii[0], radii[1], color=color,
                     linewidth=linewidth,
                     linestyle=linestyle, alpha=alpha,
                     coord=coord, rot_deg=rot_deg)
        obj1.editable = False

        obj2 = klass(pt[0], pt[1], oxradius, oyradius, color=color,
                     linewidth=linewidth,
                     linestyle=linestyle, alpha=alpha,
                     coord=coord, rot_deg=rot_deg)
        obj2.editable = False

        points = np.asarray([pt], dtype=float)

        CompoundObject.__init__(self, obj1, obj2,
                                points=points, xradius=xradius, yradius=yradius,
                                xwidth=xwidth, ywidth=ywidth, color=color,
                                linewidth=linewidth, linestyle=linestyle,
                                alpha=alpha, rot_deg=rot_deg, **kwdargs)
        OnePointTwoRadiusMixin.__init__(self)

        self.editable = True
        self.opaque = True
        self.atype = atype
        self.kind = 'annulus2r'

    def get_edit_points(self, viewer):
        move_pt, scale_pt, rotate_pt = self.get_move_scale_rotate_pts(viewer)

        points = (self.crdmap.offset_pt((self.x, self.y),
                                        (self.xradius, 0)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (0, self.yradius)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (self.xradius + self.xwidth, 0)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (0, self.yradius + self.ywidth)),
                  )
        points = self.get_data_points(points=points)
        return [move_pt,    # location
                Point(*points[0]),  # adj inner X radius
                Point(*points[1]),  # adj inner Y radius
                Point(*points[2]),  # adj X width
                Point(*points[3]),  # adj Y width
                scale_pt,
                rotate_pt,
                ]

    def setup_edit(self, detail):
        detail.center_pos = self.get_center_pt()
        detail.xradius = self.xradius
        detail.yradius = self.yradius
        detail.xwidth = self.xwidth
        detail.ywidth = self.ywidth

    def set_edit_point(self, i, pt, detail):
        if i == 0:
            self.move_to_pt(pt)
        elif i == 1:
            # Adjust inner X radius
            scale_x, scale_y = self.calc_dual_scale_from_pt(pt, detail)
            self.xradius = detail.xradius * scale_x
            #scalef = self.calc_scale_from_pt(pt, detail)
            # inner obj radius control pt
            #self.xradius = detail.xradius * scalef
        elif i == 2:
            # Adjust inner Y radius
            scale_x, scale_y = self.calc_dual_scale_from_pt(pt, detail)
            self.yradius = detail.yradius * scale_y
            #scalef = self.calc_scale_from_pt(pt, detail)
            #self.yradius = detail.yradius * scalef
        elif i == 3:
            # Adjust X width
            scale_x, scale_y = self.calc_dual_scale_from_pt(pt, detail)
            xwidth = detail.xwidth * scale_x
            # outer obj radius control pt--calculate new width
            assert xwidth > 0, ValueError("Must have a positive width")
            self.xwidth = xwidth
        elif i == 4:
            # Adjust Y width
            scale_x, scale_y = self.calc_dual_scale_from_pt(pt, detail)
            ywidth = detail.ywidth * scale_y
            # outer obj radius control pt--calculate new width
            assert ywidth > 0, ValueError("Must have a positive width")
            self.ywidth = ywidth
        elif i == 5:
            # Adjust overall scale
            scalef = self.calc_scale_from_pt(pt, detail)
            self.xradius = detail.xradius * scalef
            self.yradius = detail.yradius * scalef
        elif i == 6:
            # Adjust rotation
            delta_deg = self.calc_rotation_from_pt(pt, detail)
            self.rotate_by_deg([delta_deg])
        else:
            raise ValueError("No point corresponding to index %d" % (i))

        self.sync_state()

    def sync_state(self):
        """Called to synchronize state (e.g. when parameters have changed).
        """
        oxradius = self.xradius + self.xwidth
        oyradius = self.yradius + self.ywidth
        if oxradius < self.xradius or oyradius < self.yradius:
            raise ValueError('Outer boundary < inner boundary')

        d = dict(points=self.points, xradius=self.xradius,
                 yradius=self.yradius, color=self.color,
                 linewidth=self.linewidth, linestyle=self.linestyle,
                 alpha=self.alpha, rot_deg=self.rot_deg,
                 coord=self.coord, crdmap=self.crdmap)

        # update inner object
        self.objects[0].__dict__.update(d)

        # update outer object
        d['xradius'] = oxradius
        d['yradius'] = oyradius
        self.objects[1].__dict__.update(d)

    def move_to_pt(self, dst_pt):
        super(Annulus2RP, self).move_to_pt(dst_pt)

        self.set_data_points([dst_pt])


class Annulus2R(Annulus2RP):

    @classmethod
    def idraw(cls, canvas, cxt):
        xradius, yradius = abs(cxt.start_x - cxt.x), abs(cxt.start_y - cxt.y)
        return cls(cxt.start_x, cxt.start_y, xradius, yradius,
                   **cxt.drawparams)

    def __init__(self, x, y, xradius, yradius, xwidth=None,
                 ywidth=None, atype='ellipse', color='yellow',
                 linewidth=1, linestyle='solid', alpha=1.0,
                 rot_deg=0.0, **kwdargs):
        Annulus2RP.__init__(self, (x, y), (xradius, yradius),
                            xwidth=xwidth, ywidth=ywidth, atype=atype,
                            color=color, linewidth=linewidth,
                            linestyle=linestyle, alpha=alpha,
                            rot_deg=rot_deg, **kwdargs)


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
            Param(name='fontsize', type=float, default=8.0,
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
        self._cur_limits = ((0.0, 0.0), (0.0, 0.0))
        self._cur_images = set([])

        CompoundObject.__init__(self,
                                color=color, alpha=alpha,
                                linewidth=linewidth, linestyle=linestyle,
                                font=font, fontsize=fontsize, **kwdargs)

        self.editable = False
        self.pickable = False
        self.opaque = True
        self.kind = 'wcsaxes'

    def _calc_axes(self, viewer, images, rot_deg, swapxy, limits):
        self.logger.debug("recalculating axes...")
        self._cur_images = images
        self._cur_rot = rot_deg
        self._cur_swap = swapxy
        self._cur_limits = limits

        image = viewer.get_image()
        if image is None or not image.has_valid_wcs():
            self.logger.debug(
                'WCSAxes can only be displayed for image with valid WCS')
            return []

        x1, y1 = limits[0][:2]
        x2, y2 = limits[1][:2]
        min_imsize = min(x2 - x1, y2 - y1)
        if min_imsize <= 0:
            self.logger.debug('Cannot draw WCSAxes on image with 0 dim')
            return []

        # Approximate bounding box in RA/DEC space
        try:
            radec = image.wcs.datapt_to_system(
                [(x1, y1), (x1, y2), (x2, y1), (x2, y2)],
                naxispath=image.naxispath)
        except Exception as e:
            self.logger.warning('WCSAxes failed: {}'.format(str(e)))
            return []
        ra_min, dec_min = radec.ra.min().deg, radec.dec.min().deg
        ra_max, dec_max = radec.ra.max().deg, radec.dec.max().deg
        ra_size = ra_max - ra_min
        dec_size = dec_max - dec_min

        # Calculate positions of RA/DEC lines
        d_ra = ra_size / (self.num_ra + 1)
        d_dec = dec_size / (self.num_dec + 1)
        ra_arr = np.arange(ra_min + d_ra, ra_max - d_ra * 0.5, d_ra)
        dec_arr = np.arange(dec_min + d_dec, dec_max - d_ra * 0.5, d_dec)

        # RA/DEC step size for each vector
        d_ra_step = ra_size * self._pix_res / min_imsize
        d_dec_step = dec_size * self._pix_res / min_imsize

        # Create Path objects
        objs = []

        for cur_ra in ra_arr:
            crds = [[cur_ra, cur_dec] for cur_dec in
                    np.arange(dec_min, dec_max + d_dec_step, d_dec_step)]
            lbl = ra_deg_to_str(cur_ra)
            objs += self._get_path(viewer, image, crds, lbl, 1)
        for cur_dec in dec_arr:
            crds = [[cur_ra, cur_dec] for cur_ra in
                    np.arange(ra_min, ra_max + d_ra_step, d_ra_step)]
            lbl = dec_deg_to_str(cur_dec)
            objs += self._get_path(viewer, image, crds, lbl, 0)

        return objs

    def _get_path(self, viewer, image, crds, lbl, axis):
        from ginga.canvas.types.basic import Path, Text

        try:
            pts = image.wcs.wcspt_to_datapt(crds, naxispath=image.naxispath)
        except Exception as e:
            self.logger.warning('WCSAxes failed: {}'.format(str(e)))
            return []

        (x1, y1), (x2, y2) = viewer.get_limits()
        # Don't draw outside image area
        mask = ((pts[:, 0] >= x1) & (pts[:, 0] <= x2) &
                (pts[:, 1] >= y1) & (pts[:, 1] <= y2))
        pts = pts[mask]

        if len(pts) == 0:
            self.logger.debug(
                'All WCSAxes coords ({}) out of bound in {}x{} '
                'image'.format(crds, image.width, image.height))
            return []

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
                if np.isfinite(m):
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
        canvas = viewer.get_canvas()
        vip = viewer.get_vip()
        cvs_imgs = vip.get_images([], canvas)
        images = set([cvs_img.get_image() for cvs_img in cvs_imgs])
        diff = images.difference(self._cur_images)
        update = len(diff) > 0

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

        cur_limits = viewer.get_limits()
        if not np.all(np.isclose(cur_limits, self._cur_limits)):
            # limits have changed
            update = True

        if len(self.objects) == 0:
            # initial time
            update = True

        if update:
            # only expensive recalculation of grid if needed
            self.ra_angle = None
            self.dec_angle = None
            self.objects = self._calc_axes(viewer, images, cur_rot, cur_swap,
                                           cur_limits)

        super(WCSAxes, self).draw(viewer)


register_canvas_types(dict(ruler=Ruler, compass=Compass,
                           crosshair=Crosshair, annulus=Annulus,
                           annulus2r=Annulus2R, wcsaxes=WCSAxes))

# END
