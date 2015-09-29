#
# astro.py -- classes for special astronomy shapes drawn on
#                   ginga canvases.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import numpy

from ginga.canvas.CanvasObject import (CanvasObjectBase, _bool, _color,
                                       register_canvas_types, get_canvas_type,
                                       colors_plus_none)
from ginga.misc.ParamSet import Param
from ginga.misc.Bunch import Bunch
from ginga.util import wcs

from .basic import TwoPointMixin, OnePointOneRadiusMixin
from .layer import CompoundObject

class Ruler(TwoPointMixin, CanvasObjectBase):
    """Draws a WCS ruler (like a right triangle) on a DrawingCanvas.
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
        return [(self.x1, self.y1), (self.x2, self.y2)]

    def select_contains(self, viewer, data_x, data_y):
        x1, y1 = self.crdmap.to_data(self.x1, self.y1)
        x2, y2 = self.crdmap.to_data(self.x2, self.y2)
        return self.within_line(viewer, data_x, data_y, x1, y1, x2, y2,
                                self.cap_radius)

    def get_ruler_distances(self, viewer):
        mode = self.units.lower()
        try:
            image = viewer.get_image()
            if mode in ('arcmin', 'degrees'):
                # Calculate RA and DEC for the three points
                # origination point
                ra_org, dec_org = image.pixtoradec(self.x1, self.y1)

                # destination point
                ra_dst, dec_dst = image.pixtoradec(self.x2, self.y2)

                # "heel" point making a right triangle
                ra_heel, dec_heel = image.pixtoradec(self.x2, self.y1)

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
                    text_h = str(sep_h)
                    sep_x = wcs.deltaStarsRaDecDeg(ra_org, dec_org,
                                                   ra_heel, dec_heel)
                    text_x = str(sep_x)
                    sep_y = wcs.deltaStarsRaDecDeg(ra_heel, dec_heel,
                                                    ra_dst, dec_dst)
                    text_y = str(sep_y)
            else:
                dx = abs(self.x2 - self.x1)
                dy = abs(self.y2 - self.y1)
                dh = math.sqrt(dx**2 + dy**2)
                text_x = str(dx)
                text_y = str(dy)
                text_h = ("%.3f" % dh)

        except Exception as e:
            text_h = 'BAD WCS'
            text_x = 'BAD WCS'
            text_y = 'BAD WCS'

        return (text_x, text_y, text_h)

    def draw(self, viewer):
        cx1, cy1 = self.canvascoords(viewer, self.x1, self.y1)
        cx2, cy2 = self.canvascoords(viewer, self.x2, self.y2)

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
            show_angle = 0
        elif cy1 < cy2:
            xplumb_yoffset = -4
        else:
            xplumb_yoffset = 14
            diag_yoffset = -4

        if abs(cx1 - cx2) < 5:
            diag_xoffset = -(4 + htwd)
            show_angle = 0
        elif (cx1 < cx2):
            diag_xoffset = -(4 + htwd)
            yplumb_xoffset = 4
        else:
            diag_xoffset = 4
            yplumb_xoffset = -(4 + ytwd)

        xh = min(cx1, cx2); y = cy1 + xplumb_yoffset
        xh += (max(cx1, cx2) - xh) // 2
        yh = min(cy1, cy2); x = cx2 + yplumb_xoffset
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
    """Draws a WCS compass on a DrawingCanvas.
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
        image = self.viewer.get_image()
        x, y, xn, yn, xe, ye = image.calc_compass_radius(self.x,
                                                         self.y,
                                                         self.radius)
        return [(x, y), (xn, yn), (xe, ye)]

    def get_edit_points(self):
        return self.get_points()

    def set_edit_point(self, i, pt):
        if i == 0:
            self.set_point_by_index(i, pt)
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
        (cx1, cy1), (cx2, cy2), (cx3, cy3) = self.get_cpoints(viewer)
        cr = viewer.renderer.setup_cr(self)
        cr.set_font_from_shape(self)

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

        xh = min(cx1, cx2); y = cy1 + xplumb_yoffset
        xh += (max(cx1, cx2) - xh) // 2
        yh = min(cy1, cy2); x = cx2 + yplumb_xoffset
        yh += (max(cy1, cy2) - yh) // 2

        xd = xh + diag_xoffset
        yd = yh + diag_yoffset
        return (xd, yd)


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
    """Special compound object to handle annulus shape that
    consists of two objects with the same centroid.

    Examples
    --------
    >>> tag = canvas.add(Annulus(100, 200, 10, width=5, atype='circle'))
    >>> obj = canvas.getObjectByTag(tag)
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
            Param(name='width', type=float, default=5,
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
                            abs(cxt.start_y - cxt.y)**2 )
        return cls(cxt.start_x, cxt.start_y, radius,
                   **cxt.drawparams)

    def __init__(self, x, y, radius, width=None,
                 atype='circle', color='yellow',
                 linewidth=1, linestyle='solid', alpha=1.0,
                 **kwdargs):

        if width is None:
            width = 0.15 * radius
        oradius = radius + width

        if oradius < radius:
            raise ValueError('Outer boundary < inner boundary')

        CanvasObjectBase.__init__(self, x=x, y=y, radius=radius,
                                  width=width, color=color,
                                  linewidth=linewidth, linestyle=linestyle,
                                  alpha=alpha, **kwdargs)

        klass = get_canvas_type(atype)
        obj1 = klass(x, y, radius, color=color,
                     linewidth=linewidth,
                     linestyle=linestyle, alpha=alpha)
        obj1.editable = False

        obj2 = klass(x, y, oradius, color=color,
                     linewidth=linewidth,
                     linestyle=linestyle, alpha=alpha)
        obj2.editable = False

        CompoundObject.__init__(self, obj1, obj2)
        OnePointOneRadiusMixin.__init__(self)

        self.editable = True
        self.opaque = True
        self.kind = 'annulus'

    def get_edit_points(self):
        return [(self.x, self.y),
                (self.x + self.radius, self.y),
                (self.x + self.radius + self.width, self.y)]

    def set_edit_point(self, i, pt):
        if i == 0:
            # move control point
            self.set_point_by_index(i, pt)
        else:
            x, y = pt
            radius = math.sqrt(abs(x - self.x)**2 +
                               abs(y - self.y)**2 )
            if i == 1:
                # inner obj radius control pt
                self.radius = radius
            elif i == 2:
                # outer obj radius control pt--calculate new width
                width = radius - self.radius
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
        self.x = xdst
        self.y = ydst


register_canvas_types(dict(ruler=Ruler, compass=Compass,
                           annulus=Annulus))

#END
