#
# basic.py -- classes for basic shapes drawn on ginga canvases.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import numpy as np

from ginga.canvas.CanvasObject import (CanvasObjectBase, _bool, _color,
                                       Point as XPoint, MovePoint, ScalePoint,
                                       EditPoint,
                                       register_canvas_types,
                                       colors_plus_none, coord_names)
from ginga import trcalc
from ginga.misc.ParamSet import Param
from ginga.util import bezier

from .mixins import (OnePointMixin, TwoPointMixin, OnePointOneRadiusMixin,
                     OnePointTwoRadiusMixin, PolygonMixin)


#
#   ==== BASIC CLASSES FOR GRAPHICS OBJECTS ====
#
class TextP(OnePointMixin, CanvasObjectBase):
    """Draws text on a DrawingCanvas.

    Parameters are:
    x, y: 0-based coordinates in the data space
    text: the text to draw
    Optional parameters for fontsize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='coord', type=str, default='data',
                  valid=coord_names,
                  description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of lower left of text"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of lower left of text"),
            Param(name='text', type=str, default='EDIT ME',
                  description="Text to display"),
            Param(name='font', type=str, default='Sans Serif',
                  description="Font family for text"),
            Param(name='fontsize', type=float, default=None,
                  min=2, max=144,
                  description="Font size of text (default: vary by scale)"),
            Param(name='fontsize_min', type=float, default=6.0,
                  min=2, max=144,
                  description="Minimum font size of text (if not fixed)"),
            Param(name='fontsize_max', type=float, default=None,
                  min=2, max=144,
                  description="Maximum font size of text (if not fixed)"),
            Param(name='fontscale', type=_bool,
                  default=False, valid=[False, True],
                  description="Scale font with scale of viewer"),
            Param(name='color',
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of text"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of text"),
            Param(name='rot_deg', type=float, default=0.0,
                  min=-359.999, max=359.999, widget='spinfloat', incr=1.0,
                  description="Rotation of text"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        return cls((cxt.start_x, cxt.start_y), **cxt.drawparams)

    def __init__(self, pt, text='EDIT ME',
                 font='Sans Serif', fontsize=None, fontscale=False,
                 fontsize_min=6.0, fontsize_max=None,
                 color='yellow', alpha=1.0, rot_deg=0.0,
                 showcap=False, **kwdargs):
        self.kind = 'text'
        points = np.asarray([pt], dtype=float)
        super(TextP, self).__init__(points=points, color=color, alpha=alpha,
                                    font=font, fontsize=fontsize,
                                    fontscale=fontscale,
                                    fontsize_min=fontsize_min,
                                    fontsize_max=fontsize_max,
                                    text=text, rot_deg=rot_deg,
                                    showcap=showcap, **kwdargs)
        OnePointMixin.__init__(self)

    def set_edit_point(self, i, pt, detail):
        if i == 0:
            self.move_to_pt(pt)
        elif i == 1:
            scalef = self.calc_scale_from_pt(pt, detail)
            self.fontsize = detail.fontsize * scalef
        elif i == 2:
            delta_deg = self.calc_rotation_from_pt(pt, detail)
            self.rot_deg = math.fmod(self.rot_deg + delta_deg, 360.0)
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def scale_by_factors(self, factors):
        fontsize = 10.0 if self.fontsize is None else self.fontsize
        self.fontsize = fontsize * factors[0]

    def rotate_by_deg(self, thetas):
        self.rot_deg += thetas[0]

    def setup_edit(self, detail):
        detail.center_pos = self.get_center_pt()
        fontsize = self.fontsize
        if fontsize is None:
            fontsize = 10.0
        detail.fontsize = fontsize
        detail.rot_deg = self.rot_deg

    def get_edit_points(self, viewer):
        move_pt, scale_pt, rotate_pt = self.get_move_scale_rotate_pts(viewer)
        return [move_pt,
                scale_pt,
                rotate_pt,
                ]

    def select_contains_pt(self, viewer, pt):
        x1, y1, x2, y2 = self._get_unrotated_text_llur(viewer)
        # rotate point back to non-rotated cartesian alignment for test
        x, y = trcalc.rotate_pt(pt[0], pt[1], -self.rot_deg,
                                xoff=x1, yoff=y1)

        return (min(x1, x2) <= x and x <= max(x1, x2) and
                min(y1, y2) <= y and y <= max(y1, y2))

    def _get_unrotated_text_llur(self, viewer):
        # convert coordinate to data point and then pixel pt
        x1, y1 = self.get_data_points()[0]
        cx1, cy1 = viewer.tform['data_to_native'].to_((x1, y1))
        # width and height of text define bbox
        wd_px, ht_px = viewer.renderer.get_dimensions(self)
        cx2, cy2 = cx1 + wd_px, cy1 - ht_px
        # convert back to data points and construct bbox
        x2, y2 = viewer.tform['data_to_native'].from_((cx2, cy2))
        x1, y1, x2, y2 = self.swapxy(x1, y1, x2, y2)
        return (x1, y1, x2, y2)

    def get_llur(self):
        x, y = self.get_data_points()[0]
        r = 20
        (x1, y1), (x2, y2) = (x - r, y - r), (x + r, y + r)
        return self.swapxy(x1, y1, x2, y2)

    def draw(self, viewer):
        cr = viewer.renderer.setup_cr(self)
        cr.set_font_from_shape(self)

        x, y = self.get_data_points()[0]
        cx, cy = viewer.get_canvas_xy(x, y)
        cr.draw_text(cx, cy, self.text, rot_deg=self.rot_deg)


class Text(TextP):

    @classmethod
    def idraw(cls, canvas, cxt):
        return cls(cxt.start_x, cxt.start_y, **cxt.drawparams)

    def __init__(self, x, y, text='EDIT ME',
                 font='Sans Serif', fontsize=None, fontscale=False,
                 fontsize_min=6.0, fontsize_max=None,
                 color='yellow', alpha=1.0, rot_deg=0.0,
                 showcap=False, **kwdargs):
        TextP.__init__(self, (x, y), text=text, color=color, alpha=alpha,
                       font=font, fontsize=fontsize, fontscale=fontscale,
                       fontsize_min=fontsize_min, fontsize_max=fontsize_max,
                       rot_deg=rot_deg, showcap=showcap, **kwdargs)


class Polygon(PolygonMixin, CanvasObjectBase):
    """Draws a polygon on a DrawingCanvas.
    Parameters are:
    List of (x, y) points in the polygon.  The last one is assumed to
    be connected to the first.
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='coord', type=str, default='data',
                  valid=coord_names,
                  description="Set type of coordinates"),
            ## Param(name='points', type=list, default=[], argpos=0,
            ##       description="points making up polygon"),
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
            Param(name='fill', type=_bool,
                  default=False, valid=[False, True],
                  description="Fill the interior"),
            Param(name='fillcolor', default=None,
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        points = list(cxt.points)
        points.append(XPoint(cxt.x, cxt.y))
        if len(points) < 3:
            # we need at least 3 points for a polygon, so
            # revert to a line if we haven't got enough
            klass = canvas.get_draw_class('line')
            return klass(cxt.start_x, cxt.start_y, cxt.x, cxt.y,
                         **cxt.drawparams)
        else:
            return cls(points, **cxt.drawparams)

    def __init__(self, points, color='red',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0,
                 fillalpha=1.0, **kwdargs):
        self.kind = 'polygon'

        CanvasObjectBase.__init__(self, points=points, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle, alpha=alpha,
                                  fill=fill, fillcolor=fillcolor,
                                  fillalpha=fillalpha, **kwdargs)
        PolygonMixin.__init__(self)

        assert len(points) > 2, ValueError("Polygons need at least 3 points")

    def draw(self, viewer):
        cr = viewer.renderer.setup_cr(self)

        cpoints = self.get_cpoints(viewer)

        cr.draw_polygon(cpoints)

        if self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Path(PolygonMixin, CanvasObjectBase):
    """Draws a path on a DrawingCanvas.
    Parameters are:
    List of (x, y) points in the polygon.
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='coord', type=str, default='data',
                  valid=coord_names,
                  description="Set type of coordinates"),
            ## Param(name='points', type=list, default=[], argpos=0,
            ##       description="points making up polygon"),
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
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        points = list(cxt.points)
        points.append((cxt.x, cxt.y))
        return cls(points, **cxt.drawparams)

    def __init__(self, points, color='red',
                 linewidth=1, linestyle='solid', showcap=False,
                 alpha=1.0, **kwdargs):
        self.kind = 'path'

        CanvasObjectBase.__init__(self, points=points, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle, alpha=alpha,
                                  **kwdargs)
        PolygonMixin.__init__(self)

    def contains_pts_path(self, points, path_points, radius=1.0):
        # This code is split out of contains_pts() so that it can
        # be called from BezierCurve with a different set of path
        # points.
        p_start = path_points[0]
        points = np.asarray(points)
        contains = None
        for ppt in path_points[1:]:
            p_stop = ppt
            res = self.point_within_line(points, p_start, p_stop, radius)
            if contains is None:
                contains = res
            else:
                contains = np.logical_or(contains, res)
            p_start = p_stop
        return contains

    def contains_pts(self, points, radius=1.0):
        return self.contains_pts_path(points, self.points, radius=radius)

    def select_contains_path(self, viewer, path_points, pt):
        # This code is split out so that it can be called from
        # BezierCurve with a different set of points
        p_start = path_points[0]
        for point in path_points[1:]:
            p_stop = point
            if self.within_line(viewer, pt, p_start, p_stop, self.cap_radius):
                return True
            p_start = p_stop
        return False

    def select_contains_pt(self, viewer, pt):
        path_points = self.get_data_points()
        return self.select_contains_path(viewer, path_points, pt)

    def draw(self, viewer):
        cpoints = self.get_cpoints(viewer)

        cr = viewer.renderer.setup_cr(self)
        cr.draw_path(cpoints)

        if self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class FreePolygon(Polygon):

    @classmethod
    def idraw(cls, canvas, cxt):
        cxt.points.append((cxt.x, cxt.y))
        points = list(cxt.points)
        return cls(points, **cxt.drawparams)


class FreePath(Path):

    @classmethod
    def idraw(cls, canvas, cxt):
        cxt.points.append((cxt.x, cxt.y))
        points = list(cxt.points)
        return cls(points, **cxt.drawparams)


class BezierCurve(Path):
    """Draws a Bezier Curve on a DrawingCanvas.
    Parameters are:
    List of (x, y) points in the curve.
    Optional parameters for linesize, color, etc.

    TODO: need to implement contains_pt(), which means figuring out whether a
    point lies on a bezier curve.
        See http://polymathprogrammer.com/2012/04/03/does-point-lie-on-bezier-curve/
    """

    @classmethod
    def idraw(cls, canvas, cxt):
        points = list(cxt.points)
        points.append((cxt.x, cxt.y))
        return cls(points, **cxt.drawparams)

    def __init__(self, points, color='red',
                 linewidth=1, linestyle='solid', showcap=False,
                 alpha=1.0, **kwdargs):
        self.kind = 'beziercurve'

        CanvasObjectBase.__init__(self, points=points, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle, alpha=alpha,
                                  **kwdargs)
        PolygonMixin.__init__(self)

    def get_points_on_curve(self, image):
        points = list(self.get_data_points())
        # use maximum dimension of image to estimate a reasonable number
        # of intermediate points
        #steps = max(*image.get_size())
        steps = bezier.bezier_steps
        return list(bezier.get_4pt_bezier(steps, points))

    def select_contains_pt(self, viewer, pt):
        image = viewer.get_image()
        path_points = self.get_points_on_curve(image)
        return self.select_contains_path(viewer, path_points, pt)

    # TODO: this probably belongs somewhere else
    def get_pixels_on_curve(self, image, getvalues=True):
        data = image.get_data()
        wd, ht = image.get_size()
        if getvalues:
            res = [data[int(y), int(x)]
                   if 0 <= x < wd and 0 <= y < ht else np.NaN
                   for x, y in self.get_points_on_curve(image)]
        else:
            res = [(int(x), int(y))
                   if 0 <= x < wd and 0 <= y < ht else np.NaN
                   for x, y in self.get_points_on_curve(image)]
        return res

    def draw(self, viewer):
        cpoints = self.get_cpoints(viewer)

        cr = viewer.renderer.setup_cr(self)
        if len(cpoints) < 4:
            # until we have 4 points, we cannot draw a quadradic bezier curve
            cr.draw_path(cpoints)
        else:
            if hasattr(cr, 'draw_bezier_curve'):
                cr.draw_bezier_curve(cpoints)

            else:
                # No Bezier support in this backend, so calculate intermediate
                # points and draw a path
                #steps = max(*viewer.get_window_size())
                steps = bezier.bezier_steps
                ipoints = list(bezier.get_4pt_bezier(steps, cpoints))
                cr.draw_path(ipoints)

        if self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class BoxP(OnePointTwoRadiusMixin, CanvasObjectBase):
    """Draws a box on a DrawingCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    xradius, yradius: radii based on the number of pixels in data space
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
            Param(name='xradius', type=float, default=1.0, argpos=2,
                  min=0.0,
                  description="X radius of object"),
            Param(name='yradius', type=float, default=1.0, argpos=3,
                  min=0.0,
                  description="Y radius of object"),
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
            Param(name='fill', type=_bool,
                  default=False, valid=[False, True],
                  description="Fill the interior"),
            Param(name='fillcolor', default=None,
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            Param(name='rot_deg', type=float, default=0.0,
                  min=-359.999, max=359.999, widget='spinfloat', incr=1.0,
                  description="Rotation about center of object"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        xradius, yradius = abs(cxt.start_x - cxt.x), abs(cxt.start_y - cxt.y)
        return cls((cxt.start_x, cxt.start_y), (xradius, yradius),
                   **cxt.drawparams)

    def __init__(self, pt, radii, color='red',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 rot_deg=0.0, **kwdargs):
        xradius, yradius = radii[:2]
        points = np.asarray([pt], dtype=float)
        CanvasObjectBase.__init__(self, points=points, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  alpha=alpha, fillalpha=fillalpha,
                                  xradius=xradius, yradius=yradius,
                                  rot_deg=rot_deg,
                                  **kwdargs)
        OnePointTwoRadiusMixin.__init__(self)
        self.kind = 'box'

    def get_points(self):
        points = (self.crdmap.offset_pt((self.x, self.y),
                                        (-self.xradius, -self.yradius)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (self.xradius, -self.yradius)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (self.xradius, self.yradius)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (-self.xradius, self.yradius)),
                  )
        points = self.get_data_points(points=points)
        return points

    def contains_pts(self, pts):
        x_arr, y_arr = np.asarray(pts).T

        points = self.get_points()
        x1, y1 = points[0]
        x2, y2 = points[2]

        # rotate points back to non-rotated cartesian alignment for test
        xd, yd = self.crdmap.to_data((self.x, self.y))
        xa, ya = trcalc.rotate_pt(x_arr, y_arr, -self.rot_deg,
                                  xoff=xd, yoff=yd)

        contains = np.logical_and(
            np.logical_and(min(x1, x2) <= xa, xa <= max(x1, x2)),
            np.logical_and(min(y1, y2) <= ya, ya <= max(y1, y2)))
        return contains

    def draw(self, viewer):
        cpoints = self.get_cpoints(viewer)

        cr = viewer.renderer.setup_cr(self)
        cr.draw_polygon(cpoints)

        if self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Box(BoxP):

    @classmethod
    def idraw(cls, canvas, cxt):
        xradius, yradius = abs(cxt.start_x - cxt.x), abs(cxt.start_y - cxt.y)
        return cls(cxt.start_x, cxt.start_y, xradius, yradius,
                   **cxt.drawparams)

    def __init__(self, x, y, xradius, yradius, color='red',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 rot_deg=0.0, **kwdargs):
        BoxP.__init__(self, (x, y), (xradius, yradius), color=color,
                      linewidth=linewidth, showcap=showcap,
                      linestyle=linestyle,
                      fill=fill, fillcolor=fillcolor,
                      alpha=alpha, fillalpha=fillalpha,
                      rot_deg=rot_deg,
                      **kwdargs)


class SquareBoxP(OnePointOneRadiusMixin, CanvasObjectBase):
    """Draws a square box on a DrawingCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    radius: radius based on the number of pixels in data space
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
                  description="radius of object"),
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
            Param(name='fill', type=_bool,
                  default=False, valid=[False, True],
                  description="Fill the interior"),
            Param(name='fillcolor', default=None,
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            Param(name='rot_deg', type=float, default=0.0,
                  min=-359.999, max=359.999, widget='spinfloat', incr=1.0,
                  description="Rotation about center of object"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        len_x = cxt.start_x - cxt.x
        len_y = cxt.start_y - cxt.y
        radius = max(abs(len_x), abs(len_y))
        return cls((cxt.start_x, cxt.start_y), radius, **cxt.drawparams)

    def __init__(self, pt, radius, color='red',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 rot_deg=0.0, **kwdargs):
        points = np.asarray([pt], dtype=float)
        CanvasObjectBase.__init__(self, points=points, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  alpha=alpha, fillalpha=fillalpha,
                                  radius=radius, rot_deg=rot_deg,
                                  **kwdargs)
        OnePointOneRadiusMixin.__init__(self)
        self.kind = 'squarebox'

    def get_points(self):
        points = (self.crdmap.offset_pt((self.x, self.y),
                                        (-self.radius, -self.radius)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (self.radius, -self.radius)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (self.radius, self.radius)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (-self.radius, self.radius)))
        points = self.get_data_points(points=points)
        return points

    def rotate_by_deg(self, thetas):
        new_rot = np.fmod(self.rot_deg + thetas[0], 360.0)
        self.rot_deg = new_rot
        return new_rot

    def contains_pts(self, pts):
        x_arr, y_arr = np.asarray(pts).T

        points = self.get_points()
        x1, y1 = points[0]
        x2, y2 = points[2]

        # rotate point back to cartesian alignment for test
        xd, yd = self.crdmap.to_data((self.x, self.y))
        xa, ya = trcalc.rotate_pt(x_arr, y_arr, -self.rot_deg,
                                  xoff=xd, yoff=yd)

        contains = np.logical_and(
            np.logical_and(min(x1, x2) <= xa, xa <= max(x1, x2)),
            np.logical_and(min(y1, y2) <= ya, ya <= max(y1, y2)))
        return contains

    def set_edit_point(self, i, pt, detail):
        if i == 0:
            self.set_point_by_index(i, pt)
        elif i == 1:
            scalef = self.calc_scale_from_pt(pt, detail)
            self.radius = detail.radius * scalef
        elif i == 2:
            delta_deg = self.calc_rotation_from_pt(pt, detail)
            self.rotate_by_deg([delta_deg])
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self, viewer):
        points = self.get_data_points(points=(
            self.crdmap.offset_pt((self.x, self.y),
                                  (self.radius, self.radius)),
        ))
        move_pt, scale_pt, rotate_pt = self.get_move_scale_rotate_pts(viewer)
        return [move_pt,
                ScalePoint(*points[0]),
                rotate_pt,
                ]

    def draw(self, viewer):
        cpoints = self.get_cpoints(viewer)

        cr = viewer.renderer.setup_cr(self)
        cr.draw_polygon(cpoints)

        if self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class SquareBox(SquareBoxP):

    @classmethod
    def idraw(cls, canvas, cxt):
        len_x = cxt.start_x - cxt.x
        len_y = cxt.start_y - cxt.y
        radius = max(abs(len_x), abs(len_y))
        return cls(cxt.start_x, cxt.start_y, radius, **cxt.drawparams)

    def __init__(self, x, y, radius, color='red',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 rot_deg=0.0, **kwdargs):
        SquareBoxP.__init__(self, (x, y), radius, color=color,
                            linewidth=linewidth, showcap=showcap,
                            linestyle=linestyle,
                            fill=fill, fillcolor=fillcolor,
                            alpha=alpha, fillalpha=fillalpha,
                            rot_deg=rot_deg, **kwdargs)


class EllipseP(OnePointTwoRadiusMixin, CanvasObjectBase):
    """Draws an ellipse on a DrawingCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    xradius, yradius: radii based on the number of pixels in data space
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
            Param(name='xradius', type=float, default=1.0, argpos=2,
                  min=0.0,
                  description="X radius of object"),
            Param(name='yradius', type=float, default=1.0, argpos=3,
                  min=0.0,
                  description="Y radius of object"),
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
            Param(name='fill', type=_bool,
                  default=False, valid=[False, True],
                  description="Fill the interior"),
            Param(name='fillcolor', default=None,
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            Param(name='rot_deg', type=float, default=0.0,
                  min=-359.999, max=359.999, widget='spinfloat', incr=1.0,
                  description="Rotation about center of object"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        xradius, yradius = abs(cxt.start_x - cxt.x), abs(cxt.start_y - cxt.y)
        return cls((cxt.start_x, cxt.start_y), (xradius, yradius),
                   **cxt.drawparams)

    def __init__(self, pt, radii, color='yellow',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 rot_deg=0.0, **kwdargs):
        xradius, yradius = radii
        points = np.asarray([pt], dtype=float)
        CanvasObjectBase.__init__(self, points=points, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  alpha=alpha, fillalpha=fillalpha,
                                  xradius=xradius, yradius=yradius,
                                  rot_deg=rot_deg, **kwdargs)
        OnePointTwoRadiusMixin.__init__(self)
        self.kind = 'ellipse'

    def get_points(self):
        points = ((self.x, self.y),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (self.xradius, 0)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (0, self.yradius)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (self.xradius, self.yradius)),
                  )
        points = self.get_data_points(points=points)
        return points

    def contains_pts(self, pts):
        x_arr, y_arr = np.asarray(pts).T
        x_arr, y_arr = (x_arr.astype(float, copy=False),
                        y_arr.astype(float, copy=False))

        points = self.get_points()
        # rotate point back to cartesian alignment for test
        xd, yd = points[0]
        xa, ya = trcalc.rotate_pt(x_arr, y_arr, -self.rot_deg,
                                  xoff=xd, yoff=yd)

        # need to recalculate radius in case of wcs coords
        x2, y2 = points[3]
        xradius = max(x2, xd) - min(x2, xd)
        yradius = max(y2, yd) - min(y2, yd)

        # See http://math.stackexchange.com/questions/76457/check-if-a-point-is-within-an-ellipse
        res = (((xa - xd) ** 2) / xradius ** 2 +
               ((ya - yd) ** 2) / yradius ** 2)
        contains = (res <= 1.0)
        return contains

    def get_wdht(self):
        # See http://stackoverflow.com/questions/87734/how-do-you-calculate-the-axis-aligned-bounding-box-of-an-ellipse
        theta = np.radians(self.rot_deg)
        sin_theta = np.sin(theta)
        cos_theta = np.cos(theta)

        # need to recalculate radius in case of wcs coords
        points = self.get_points()
        x, y = points[0]
        xradius = abs(points[1][0] - x)
        yradius = abs(points[2][1] - y)

        a = xradius * cos_theta
        b = yradius * sin_theta
        c = xradius * sin_theta
        d = yradius * cos_theta
        wd = np.sqrt(a ** 2.0 + b ** 2.0) * 2.
        ht = np.sqrt(c ** 2.0 + d ** 2.0) * 2.

        return (points, (wd, ht))

    def get_llur(self):
        points, dims = self.get_wdht()
        x, y = points[0]
        wd, ht = dims

        x1, y1 = x - wd * 0.5, y + ht * 0.5
        x2, y2 = x1 + wd, y1 - ht
        return self.swapxy(x1, y1, x2, y2)

    def get_bezier_pts(self, points, rot_deg=None):
        x, y = points[0]
        xradius = abs(points[1][0] - x)
        yradius = abs(points[2][1] - y)

        pts = np.asarray(bezier.get_bezier_ellipse(x, y, xradius, yradius))
        if rot_deg is None:
            return pts

        # specified a rotation for the points
        return trcalc.rotate_coord(pts, [rot_deg], (x, y))

    def draw(self, viewer):
        cr = viewer.renderer.setup_cr(self)

        if hasattr(cr, 'draw_ellipse'):
            # <- backend can draw rotated ellipses
            cpoints = self.get_cpoints(viewer,
                                       points=self.get_edit_points(viewer))
            cx, cy = cpoints[0]
            cxradius = abs(cpoints[1][0] - cx)
            cyradius = abs(cpoints[2][1] - cy)
            cr.draw_ellipse(cx, cy, cxradius, cyradius, self.rot_deg)

        elif hasattr(cr, 'draw_ellipse_bezier'):
            # <- backend can draw Bezier curves
            points = self.get_bezier_pts(self.get_points())
            cp = self.get_cpoints(viewer, points=points)
            cr.draw_ellipse_bezier(cp)

        else:
            # <- backend can draw polygons
            points = self.get_bezier_pts(self.get_points())
            cp = self.get_cpoints(viewer, points=points)
            num_pts = bezier.bezier_steps
            cp = bezier.get_bezier(num_pts, cp)
            cr.draw_polygon(cp)

        if self.showcap:
            cpoints = self.get_cpoints(viewer)
            self.draw_caps(cr, self.cap, cpoints)


class Ellipse(EllipseP):

    @classmethod
    def idraw(cls, canvas, cxt):
        xradius, yradius = abs(cxt.start_x - cxt.x), abs(cxt.start_y - cxt.y)
        return cls(cxt.start_x, cxt.start_y, xradius, yradius,
                   **cxt.drawparams)

    def __init__(self, x, y, xradius, yradius, color='yellow',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 rot_deg=0.0, **kwdargs):
        EllipseP.__init__(self, (x, y), (xradius, yradius), color=color,
                          linewidth=linewidth, showcap=showcap,
                          linestyle=linestyle,
                          fill=fill, fillcolor=fillcolor,
                          alpha=alpha, fillalpha=fillalpha,
                          rot_deg=rot_deg, **kwdargs)


class TriangleP(OnePointTwoRadiusMixin, CanvasObjectBase):
    """Draws a triangle on a DrawingCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    xradius, yradius: radii based on the number of pixels in data space
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
            Param(name='xradius', type=float, default=1.0, argpos=2,
                  min=0.0,
                  description="X radius of object"),
            Param(name='yradius', type=float, default=1.0, argpos=3,
                  min=0.0,
                  description="Y radius of object"),
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
            Param(name='fill', type=_bool,
                  default=False, valid=[False, True],
                  description="Fill the interior"),
            Param(name='fillcolor', default=None,
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            Param(name='rot_deg', type=float, default=0.0,
                  min=-359.999, max=359.999, widget='spinfloat', incr=1.0,
                  description="Rotation about center of object"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        xradius, yradius = abs(cxt.start_x - cxt.x), abs(cxt.start_y - cxt.y)
        return cls((cxt.start_x, cxt.start_y), (xradius, yradius),
                   **cxt.drawparams)

    def __init__(self, pt, radii, color='pink',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 rot_deg=0.0, **kwdargs):
        self.kind = 'triangle'
        xradius, yradius = radii[:2]
        points = np.asarray([pt], dtype=float)
        CanvasObjectBase.__init__(self, points=points, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle, alpha=alpha,
                                  fill=fill, fillcolor=fillcolor,
                                  fillalpha=fillalpha,
                                  xradius=xradius, yradius=yradius,
                                  rot_deg=rot_deg, **kwdargs)
        OnePointTwoRadiusMixin.__init__(self)

    def get_points(self):
        points = (self.crdmap.offset_pt((self.x, self.y),
                                        (-2 * self.xradius, -self.yradius)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (2 * self.xradius, -self.yradius)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (0, self.yradius)),
                  )
        points = self.get_data_points(points=points)
        return points

    def get_llur(self):
        xd, yd = self.crdmap.to_data((self.x, self.y))
        points = np.asarray(self.get_points(), dtype=float)

        mpts = trcalc.rotate_coord(points, [self.rot_deg], [xd, yd])
        t_ = mpts.T

        x1, y1 = t_[0].min(), t_[1].min()
        x2, y2 = t_[0].max(), t_[1].max()
        return (x1, y1, x2, y2)

    def contains_pts(self, pts):
        x_arr, y_arr = np.asarray(pts).T
        x_arr, y_arr = (x_arr.astype(float, copy=False),
                        y_arr.astype(float, copy=False))
        # is this the same as self.x, self.y ?
        xd, yd = self.get_center_pt()
        # rotate point back to cartesian alignment for test
        xa, ya = trcalc.rotate_pt(x_arr, y_arr, -self.rot_deg,
                                  xoff=xd, yoff=yd)

        (x1, y1), (x2, y2), (x3, y3) = self.get_points()

        # barycentric coordinate test
        denominator = float((y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3))
        a = ((y2 - y3) * (xa - x3) + (x3 - x2) * (ya - y3)) / denominator
        b = ((y3 - y1) * (xa - x3) + (x1 - x3) * (ya - y3)) / denominator
        c = 1.0 - a - b

        #tf = (0.0 <= a <= 1.0 and 0.0 <= b <= 1.0 and 0.0 <= c <= 1.0)
        contains = np.logical_and(
            np.logical_and(0.0 <= a, a <= 1.0),
            np.logical_and(np.logical_and(0.0 <= b, b <= 1.0),
                           np.logical_and(0.0 <= c, c <= 1.0)))
        return contains

    def draw(self, viewer):
        cpoints = self.get_cpoints(viewer)

        cr = viewer.renderer.setup_cr(self)
        cr.draw_polygon(cpoints)

        if self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Triangle(TriangleP):

    @classmethod
    def idraw(cls, canvas, cxt):
        xradius, yradius = abs(cxt.start_x - cxt.x), abs(cxt.start_y - cxt.y)
        return cls(cxt.start_x, cxt.start_y, xradius, yradius,
                   **cxt.drawparams)

    def __init__(self, x, y, xradius, yradius, color='pink',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 rot_deg=0.0, **kwdargs):
        TriangleP.__init__(self, (x, y), (xradius, yradius), color=color,
                           linewidth=linewidth, showcap=showcap,
                           linestyle=linestyle, alpha=alpha,
                           fill=fill, fillcolor=fillcolor,
                           fillalpha=fillalpha,
                           rot_deg=rot_deg, **kwdargs)


class CircleP(OnePointOneRadiusMixin, CanvasObjectBase):
    """Draws a circle on a DrawingCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    radius: radius based on the number of pixels in data space
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
            Param(name='fill', type=_bool,
                  default=False, valid=[False, True],
                  description="Fill the interior"),
            Param(name='fillcolor', default=None,
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        radius = np.sqrt(abs(cxt.start_x - cxt.x) ** 2 +
                         abs(cxt.start_y - cxt.y) ** 2)
        return cls((cxt.start_x, cxt.start_y), radius, **cxt.drawparams)

    def __init__(self, pt, radius, color='yellow',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 **kwdargs):
        points = np.asarray([pt], dtype=float)
        CanvasObjectBase.__init__(self, points=points, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  alpha=alpha, fillalpha=fillalpha,
                                  radius=radius, **kwdargs)
        OnePointOneRadiusMixin.__init__(self)
        self.kind = 'circle'

    def contains_pts(self, pts):
        x_arr, y_arr = np.asarray(pts).T
        x_arr, y_arr = (x_arr.astype(float, copy=False),
                        y_arr.astype(float, copy=False))

        xd, yd = self.crdmap.to_data((self.x, self.y))

        # need to recalculate radius in case of wcs coords
        points = self.get_data_points(points=(
            self.crdmap.offset_pt((self.x, self.y), (self.radius, 0)),
            self.crdmap.offset_pt((self.x, self.y), (0, self.radius)),
        ))
        (x2, y2), (x3, y3) = points
        xradius = max(x2, xd) - min(x2, xd)
        yradius = max(y3, yd) - min(y3, yd)

        # See http://math.stackexchange.com/questions/76457/check-if-a-point-is-within-an-ellipse
        res = (((x_arr - xd) ** 2) / xradius ** 2 +
               ((y_arr - yd) ** 2) / yradius ** 2)
        contains = (res <= 1.0)
        return contains

    def get_edit_points(self, viewer):
        points = self.get_data_points(points=(
            (self.x, self.y),
            self.crdmap.offset_pt((self.x, self.y), (self.radius, 0)),
        ))
        return [MovePoint(*points[0]),
                ScalePoint(*points[1]),
                ]

    def get_llur(self):
        points = self.get_data_points(points=(
            self.crdmap.offset_pt((self.x, self.y),
                                  (-self.radius, -self.radius)),
            self.crdmap.offset_pt((self.x, self.y),
                                  (self.radius, self.radius)),
        ))
        (x1, y1), (x2, y2) = points
        return self.swapxy(x1, y1, x2, y2)

    def draw(self, viewer):
        points = self.get_data_points(points=(
            (self.x, self.y),
            self.crdmap.offset_pt((self.x, self.y), (0, self.radius)),
        ))
        cpoints = self.get_cpoints(viewer, points=points)
        cx, cy, cradius = self.calc_radius(viewer,
                                           cpoints[0], cpoints[1])
        cr = viewer.renderer.setup_cr(self)
        cr.draw_circle(cx, cy, cradius)

        if self.showcap:
            self.draw_caps(cr, self.cap, ((cx, cy), ))


class Circle(CircleP):

    @classmethod
    def idraw(cls, canvas, cxt):
        radius = np.sqrt(abs(cxt.start_x - cxt.x) ** 2 +
                         abs(cxt.start_y - cxt.y) ** 2)
        return cls(cxt.start_x, cxt.start_y, radius, **cxt.drawparams)

    def __init__(self, x, y, radius, color='yellow',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 **kwdargs):
        CircleP.__init__(self, (x, y), radius, color=color,
                         linewidth=linewidth, showcap=showcap,
                         linestyle=linestyle,
                         fill=fill, fillcolor=fillcolor,
                         alpha=alpha, fillalpha=fillalpha,
                         **kwdargs)


class PointP(OnePointOneRadiusMixin, CanvasObjectBase):
    """Draws a point on a DrawingCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    radius: radius based on the number of pixels in data space
    Optional parameters for linesize, color, style, etc.
    Currently the only styles are 'cross' and 'plus'.
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
            Param(name='style', type=str, default='cross',
                  valid=['cross', 'plus', 'circle', 'square', 'diamond',
                         'hexagon', 'downtriangle', 'uptriangle'],
                  description="Style of point (default 'cross')"),
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
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        radius = max(abs(cxt.start_x - cxt.x),
                     abs(cxt.start_y - cxt.y))
        return cls((cxt.start_x, cxt.start_y), radius, **cxt.drawparams)

    def __init__(self, pt, radius, style='cross', color='yellow',
                 linewidth=1, linestyle='solid', alpha=1.0, showcap=False,
                 **kwdargs):
        self.kind = 'point'
        points = np.asarray([pt], dtype=float)
        CanvasObjectBase.__init__(self, points=points, color=color,
                                  linewidth=linewidth, alpha=alpha,
                                  linestyle=linestyle, radius=radius,
                                  showcap=showcap, style=style,
                                  **kwdargs)
        OnePointOneRadiusMixin.__init__(self)

    def contains_pts(self, pts, radius=1.0):
        points = np.asarray(pts)
        pt = self.crdmap.to_data((self.x, self.y))
        contains = self.point_within_radius(points, pt, radius)
        return contains

    def select_contains_pt(self, viewer, pt):
        p0 = self.get_data_points()[0]
        scale = viewer.get_scale_max()
        return self.within_radius(viewer, pt, p0, self.radius * scale)

    def get_edit_points(self, viewer):
        points = self.get_data_points(points=[(self.x, self.y)])
        move_pt, scale_pt, rotate_pt = self.get_move_scale_rotate_pts(viewer)
        return [MovePoint(*points[0]), scale_pt]

    def draw(self, viewer):
        points = self.get_data_points(points=(
            (self.x, self.y),
            self.crdmap.offset_pt((self.x, self.y), (0, self.radius)),
        ))
        cpoints = self.get_cpoints(viewer, points=points)
        cx, cy, cradius = self.calc_radius(viewer,
                                           cpoints[0], cpoints[1])

        cr = viewer.renderer.setup_cr(self)

        cx1, cy1 = cx - cradius, cy - cradius
        cx2, cy2 = cx + cradius, cy + cradius

        if self.style == 'cross':
            cr.draw_line(cx1, cy1, cx2, cy2)
            cr.draw_line(cx1, cy2, cx2, cy1)

        elif self.style == 'plus':
            cr.draw_line(cx1, cy, cx2, cy)
            cr.draw_line(cx, cy1, cx, cy2)

        elif self.style == 'circle':
            cr.draw_circle(cx, cy, cradius)

        elif self.style == 'square':
            cpts = [(cx1, cy1), (cx2, cy1), (cx2, cy2), (cx1, cy2)]
            cr.draw_polygon(cpts)

        elif self.style == 'diamond':
            cpts = [(cx, cy1), ((cx + cx2) * 0.5, cy),
                    (cx, cy2), ((cx1 + cx) * 0.5, cy)]
            cr.draw_polygon(cpts)

        elif self.style == 'hexagon':
            cpts = [(cx1, cy), ((cx1 + cx) * 0.5, cy2), ((cx + cx2) * 0.5, cy2),
                    (cx2, cy), ((cx + cx2) * 0.5, cy1), ((cx1 + cx) * 0.5, cy1)]
            cr.draw_polygon(cpts)

        elif self.style == 'downtriangle':
            cpts = [(cx1, cy1), (cx2, cy1), (cx, cy2)]
            cr.draw_polygon(cpts)

        elif self.style == 'uptriangle':
            cpts = [(cx1, cy2), (cx2, cy2), (cx, cy1)]
            cr.draw_polygon(cpts)

        else:
            raise ValueError("Don't understand draw style '{}' of point".format(self.style))

        if self.showcap:
            self.draw_caps(cr, self.cap, ((cx, cy), ))


class Point(PointP):

    @classmethod
    def idraw(cls, canvas, cxt):
        radius = max(abs(cxt.start_x - cxt.x),
                     abs(cxt.start_y - cxt.y))
        return cls(cxt.start_x, cxt.start_y, radius, **cxt.drawparams)

    def __init__(self, x, y, radius, style='cross', color='yellow',
                 linewidth=1, linestyle='solid', alpha=1.0, showcap=False,
                 **kwdargs):
        PointP.__init__(self, (x, y), radius, color=color,
                        linewidth=linewidth, alpha=alpha,
                        linestyle=linestyle, showcap=showcap, style=style,
                        **kwdargs)


class RectangleP(TwoPointMixin, CanvasObjectBase):
    """Draws a rectangle on a DrawingCanvas.
    Parameters are:
    x1, y1: 0-based coordinates of one corner in the data space
    x2, y2: 0-based coordinates of the opposing corner in the data space
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='coord', type=str, default='data',
                  valid=['data', 'wcs', 'cartesian', 'window'],
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
                  description="Style of outline (default solid)"),
            Param(name='color',
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='fill', type=_bool,
                  default=False, valid=[False, True],
                  description="Fill the interior"),
            Param(name='fillcolor', default=None,
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='drawdims', type=_bool,
                  default=False, valid=[False, True],
                  description="Annotate with dimensions of object"),
            Param(name='font', type=str, default='Sans Serif',
                  description="Font family for text"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        return cls((cxt.start_x, cxt.start_y), (cxt.x, cxt.y), **cxt.drawparams)

    def __init__(self, pt1, pt2, color='red',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0,
                 drawdims=False, font='Sans Serif', fillalpha=1.0,
                 **kwdargs):
        self.kind = 'rectangle'
        points = np.asarray([pt1, pt2], dtype=float)

        CanvasObjectBase.__init__(self, points=points, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  alpha=alpha, fillalpha=fillalpha,
                                  drawdims=drawdims, font=font,
                                  **kwdargs)
        TwoPointMixin.__init__(self)

    def get_points(self):
        points = [(self.x1, self.y1), (self.x2, self.y1),
                  (self.x2, self.y2), (self.x1, self.y2)]
        points = self.get_data_points(points=points)
        return points

    def contains_pts(self, pts):
        x_arr, y_arr = np.asarray(pts).T
        x1, y1, x2, y2 = self.get_llur()

        contains = np.logical_and(
            np.logical_and(x1 <= x_arr, x_arr <= x2),
            np.logical_and(y1 <= y_arr, y_arr <= y2))
        return contains

    # TO BE DEPRECATED?
    def move_point(self):
        return self.get_center_pt()

    def draw(self, viewer):
        cr = viewer.renderer.setup_cr(self)

        cpoints = self.get_cpoints(viewer)
        cr.draw_polygon(cpoints)

        if self.drawdims:
            fontsize = self.scale_font(viewer)
            cr.set_font(self.font, fontsize, color=self.color)

            # draw label on X dimension
            pt = ((self.x1 + self.x2) * 0.5, self.y2)
            cx, cy = self.get_cpoints(viewer, points=[pt])[0]
            cr.draw_text(cx, cy, "%f" % abs(self.x2 - self.x1))

            # draw label on Y dimension
            pt = (self.x2, (self.y1 + self.y2) * 0.5)
            cx, cy = self.get_cpoints(viewer, points=[pt])[0]
            cr.draw_text(cx, cy, "%f" % abs(self.y2 - self.y1))

        if self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Rectangle(RectangleP):

    @classmethod
    def idraw(cls, canvas, cxt):
        return cls(cxt.start_x, cxt.start_y, cxt.x, cxt.y, **cxt.drawparams)

    def __init__(self, x1, y1, x2, y2, color='red',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0,
                 drawdims=False, font='Sans Serif', fillalpha=1.0,
                 **kwdargs):
        RectangleP.__init__(self, (x1, y1), (x2, y2), color=color,
                            linewidth=linewidth, showcap=showcap,
                            linestyle=linestyle,
                            fill=fill, fillcolor=fillcolor,
                            alpha=alpha, fillalpha=fillalpha,
                            drawdims=drawdims, font=font,
                            **kwdargs)


class Square(RectangleP):

    @classmethod
    def idraw(cls, canvas, cxt):
        len_x = cxt.start_x - cxt.x
        len_y = cxt.start_y - cxt.y
        length = max(abs(len_x), abs(len_y))
        len_x = np.sign(len_x) * length
        len_y = np.sign(len_y) * length
        return cls((cxt.start_x, cxt.start_y),
                   (cxt.start_x - len_x, cxt.start_y - len_y),
                   **cxt.drawparams)


class LineP(TwoPointMixin, CanvasObjectBase):
    """Draws a line on a DrawingCanvas.
    Parameters are:
    x1, y1: 0-based coordinates of one end in the data space
    x2, y2: 0-based coordinates of the opposing end in the data space
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
                  description="Style of outline (default solid)"),
            Param(name='arrow', type=str, default='none',
                  valid=['start', 'end', 'both', 'none'],
                  description="Arrows at ends (default: none)"),
            Param(name='color',
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        return cls((cxt.start_x, cxt.start_y), (cxt.x, cxt.y), **cxt.drawparams)

    def __init__(self, pt1, pt2, color='red',
                 linewidth=1, linestyle='solid', alpha=1.0,
                 arrow=None, showcap=False, **kwdargs):
        self.kind = 'line'
        points = np.asarray([pt1, pt2], dtype=float)
        CanvasObjectBase.__init__(self, points=points, color=color, alpha=alpha,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle, arrow=arrow,
                                  **kwdargs)
        TwoPointMixin.__init__(self)

    def get_points(self):
        points = [(self.x1, self.y1), (self.x2, self.y2)]
        points = self.get_data_points(points=points)
        return points

    def contains_pts(self, pts, radius=1.0):
        points = self.get_points()
        contains = self.point_within_line(pts, points[0], points[1],
                                          radius)
        return contains

    def select_contains_pt(self, viewer, pt):
        points = self.get_points()
        return self.within_line(viewer, pt, points[0], points[1],
                                self.cap_radius)

    def draw(self, viewer):
        points = self.get_points()
        x1, y1 = points[0]
        x2, y2 = points[1]
        cx1, cy1 = viewer.get_canvas_xy(x1, y1)
        cx2, cy2 = viewer.get_canvas_xy(x2, y2)

        cr = viewer.renderer.setup_cr(self)
        cr.draw_line(cx1, cy1, cx2, cy2)

        if self.arrow == 'end':
            self.draw_arrowhead(cr, cx1, cy1, cx2, cy2)
            caps = [(cx1, cy1)]
        elif self.arrow == 'start':
            self.draw_arrowhead(cr, cx2, cy2, cx1, cy1)
            caps = [(cx2, cy2)]
        elif self.arrow == 'both':
            self.draw_arrowhead(cr, cx2, cy2, cx1, cy1)
            self.draw_arrowhead(cr, cx1, cy1, cx2, cy2)
            caps = []
        else:
            caps = [(cx1, cy1), (cx2, cy2)]

        if self.showcap:
            self.draw_caps(cr, self.cap, caps)


class Line(LineP):

    @classmethod
    def idraw(cls, canvas, cxt):
        return cls(cxt.start_x, cxt.start_y, cxt.x, cxt.y, **cxt.drawparams)

    def __init__(self, x1, y1, x2, y2, color='red',
                 linewidth=1, linestyle='solid', alpha=1.0,
                 arrow=None, showcap=False, **kwdargs):
        LineP.__init__(self, (x1, y1), (x2, y2), color=color, alpha=alpha,
                       linewidth=linewidth, showcap=showcap,
                       linestyle=linestyle, arrow=arrow,
                       **kwdargs)


class RightTriangleP(TwoPointMixin, CanvasObjectBase):
    """Draws a right triangle on a DrawingCanvas.
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
                  description="Style of outline (default solid)"),
            Param(name='color',
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='fill', type=_bool,
                  default=False, valid=[False, True],
                  description="Fill the interior"),
            Param(name='fillcolor', default=None,
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        return cls((cxt.start_x, cxt.start_y), (cxt.x, cxt.y), **cxt.drawparams)

    def __init__(self, pt1, pt2, color='pink',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 **kwdargs):
        self.kind = 'righttriangle'
        points = np.asarray([pt1, pt2], dtype=float)
        CanvasObjectBase.__init__(self, points=points, color=color, alpha=alpha,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  fillalpha=fillalpha,
                                  **kwdargs)
        TwoPointMixin.__init__(self)

    def get_points(self):
        points = [(self.x1, self.y1), (self.x2, self.y2),
                  (self.x2, self.y1)]
        points = self.get_data_points(points=points)
        return points

    def contains_pts(self, pts):
        x_arr, y_arr = np.asarray(pts).T
        x_arr, y_arr = (x_arr.astype(float, copy=False),
                        y_arr.astype(float, copy=False))
        points = self.get_points()
        x1, y1 = points[0]
        x2, y2 = points[1]
        x3, y3 = points[2]

        # barycentric coordinate test
        denominator = float((y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3))
        a = ((y2 - y3) * (x_arr - x3) + (x3 - x2) * (y_arr - y3)) / denominator
        b = ((y3 - y1) * (x_arr - x3) + (x1 - x3) * (y_arr - y3)) / denominator
        c = 1.0 - a - b

        #tf = (0.0 <= a <= 1.0 and 0.0 <= b <= 1.0 and 0.0 <= c <= 1.0)
        contains = np.logical_and(
            np.logical_and(0.0 <= a, a <= 1.0),
            np.logical_and(np.logical_and(0.0 <= b, b <= 1.0),
                           np.logical_and(0.0 <= c, c <= 1.0)))
        return contains

    def draw(self, viewer):
        cpoints = self.get_cpoints(viewer)
        cr = viewer.renderer.setup_cr(self)
        cr.draw_polygon(cpoints)

        if self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class RightTriangle(RightTriangleP):

    @classmethod
    def idraw(cls, canvas, cxt):
        return cls(cxt.start_x, cxt.start_y, cxt.x, cxt.y, **cxt.drawparams)

    def __init__(self, x1, y1, x2, y2, color='pink',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 **kwdargs):
        RightTriangleP.__init__(self, (x1, y1), (x2, y2), color=color,
                                alpha=alpha, linewidth=linewidth,
                                showcap=showcap, linestyle=linestyle,
                                fill=fill, fillcolor=fillcolor,
                                fillalpha=fillalpha, **kwdargs)


class XRange(RectangleP):
    """Draws an xrange on a DrawingCanvas.
    Parameters are:
    x1: start X coordinate in the data space
    x2: end X coordinate in the data space
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
            Param(name='x2', type=float, default=0.0, argpos=1,
                  description="Second X coordinate of object"),
            Param(name='linewidth', type=int, default=0,
                  min=0, max=20, widget='spinbutton', incr=1,
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
            Param(name='fillcolor', default='aquamarine',
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=0.5,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='drawdims', type=_bool,
                  default=False, valid=[False, True],
                  description="Annotate with dimensions of object"),
            Param(name='font', type=str, default='Sans Serif',
                  description="Font family for text"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        return cls(cxt.start_x, cxt.x, **cxt.drawparams)

    def __init__(self, x1, x2, color='yellow',
                 linewidth=0, linestyle='solid', showcap=False,
                 fillcolor='aquamarine', alpha=1.0,
                 drawdims=False, font='Sans Serif', fillalpha=0.5,
                 **kwdargs):
        RectangleP.__init__(self, (x1, 0), (x2, 0), color=color,
                            linewidth=linewidth,
                            linestyle=linestyle,
                            fill=True, fillcolor=fillcolor,
                            alpha=alpha, fillalpha=fillalpha,
                            drawdims=drawdims, font=font,
                            **kwdargs)
        self.kind = 'xrange'

    def contains_pts(self, pts):
        x_arr, y_arr = np.asarray(pts).T
        x1, y1, x2, y2 = self.get_llur()

        contains = np.logical_and(x1 <= x_arr, x_arr <= x2)
        return contains

    def get_edit_points(self, viewer):
        tup = viewer.get_datarect()
        dy = (tup[1] + tup[3]) * 0.5
        pt = self.get_data_points(points=self.get_points())
        return [MovePoint((pt[0][0] + pt[2][0]) * 0.5, dy),
                EditPoint(pt[0][0], dy),
                EditPoint(pt[2][0], dy)]

    def draw(self, viewer):
        cr = viewer.renderer.setup_cr(self)

        tup = viewer.get_datarect()
        pts = [(self.x1, tup[1]), (self.x2, tup[1]),
               (self.x2, tup[3]), (self.x1, tup[3])]
        cpoints = self.get_cpoints(viewer, points=pts)

        cr.draw_polygon(cpoints)

        if self.drawdims:
            fontsize = self.scale_font(viewer)
            cr.set_font(self.font, fontsize, color=self.color)

            pt = ((self.x1 + self.x2) * 0.5, (tup[1] + tup[3]) * 0.5)
            cx, cy = self.get_cpoints(viewer, points=[pt])[0]
            cr.draw_text(cx, cy, "%f:%f" % (self.x1, self.x2))


class YRange(RectangleP):
    """Draws a yrange on a DrawingCanvas.
    Parameters are:
    y1: start Y coordinate in the data space
    y2: end Y coordinate in the data space
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='coord', type=str, default='data',
                  valid=coord_names,
                  description="Set type of coordinates"),
            Param(name='y1', type=float, default=0.0, argpos=0,
                  description="First Y coordinate of object"),
            Param(name='y2', type=float, default=0.0, argpos=1,
                  description="Second Y coordinate of object"),
            Param(name='linewidth', type=int, default=0,
                  min=0, max=20, widget='spinbutton', incr=1,
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
            Param(name='fillcolor', default='aquamarine',
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=0.5,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='drawdims', type=_bool,
                  default=False, valid=[False, True],
                  description="Annotate with dimensions of object"),
            Param(name='font', type=str, default='Sans Serif',
                  description="Font family for text"),
        ]

    @classmethod
    def idraw(cls, canvas, cxt):
        return cls(cxt.start_y, cxt.y, **cxt.drawparams)

    def __init__(self, y1, y2, color='yellow',
                 linewidth=0, linestyle='solid', showcap=False,
                 fill=True, fillcolor='aquamarine', alpha=1.0,
                 drawdims=False, font='Sans Serif', fillalpha=0.5,
                 **kwdargs):
        RectangleP.__init__(self, (0, y1), (0, y2),
                            color=color, linewidth=linewidth,
                            linestyle=linestyle,
                            fill=True, fillcolor=fillcolor,
                            alpha=alpha, fillalpha=fillalpha,
                            drawdims=drawdims, font=font,
                            **kwdargs)
        self.kind = 'yrange'

    def contains_pts(self, pts):
        x_arr, y_arr = np.asarray(pts).T
        x1, y1, x2, y2 = self.get_llur()

        contains = np.logical_and(y1 <= y_arr, y_arr <= y2)
        return contains

    def get_edit_points(self, viewer):
        tup = viewer.get_datarect()
        dx = (tup[0] + tup[2]) * 0.5
        pt = self.get_data_points(points=self.get_points())
        return [MovePoint(dx, (pt[0][1] + pt[2][1]) * 0.5),
                EditPoint(dx, pt[0][1]),
                EditPoint(dx, pt[2][1])]

    def draw(self, viewer):
        cr = viewer.renderer.setup_cr(self)

        tup = viewer.get_datarect()
        pts = [(tup[0], self.y1), (tup[2], self.y1),
               (tup[2], self.y2), (tup[0], self.y2)]
        cpoints = self.get_cpoints(viewer, points=pts)

        cr.draw_polygon(cpoints)

        if self.drawdims:
            fontsize = self.scale_font(viewer)
            cr.set_font(self.font, fontsize, color=self.color)

            pt = ((tup[0] + tup[2]) * 0.5, (self.y1 + self.y2) * 0.5)
            cx, cy = self.get_cpoints(viewer, points=[pt])[0]
            cr.draw_text(cx, cy, "%f:%f" % (self.y1, self.y2))


register_canvas_types(
    dict(text=Text, rectangle=Rectangle, circle=Circle,
         line=Line, point=Point, polygon=Polygon,
         freepolygon=FreePolygon, path=Path, freepath=FreePath,
         righttriangle=RightTriangle, triangle=Triangle,
         ellipse=Ellipse, square=Square, beziercurve=BezierCurve,
         box=Box, squarebox=SquareBox, xrange=XRange, yrange=YRange))

#END
