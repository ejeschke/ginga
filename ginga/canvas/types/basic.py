#
# basic.py -- classes for basic shapes drawn on ginga canvases.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import numpy

from ginga.canvas.CanvasObject import (CanvasObjectBase, _bool, _color,
                                       Point as XPoint, MovePoint, ScalePoint,
                                       RotatePoint,
                                       register_canvas_types,
                                       colors_plus_none)
from ginga import trcalc
from ginga.misc.ParamSet import Param
from ginga.util import wcs, bezier
from ginga.util.six.moves import map

from .mixins import (OnePointMixin, TwoPointMixin, OnePointOneRadiusMixin,
                     OnePointTwoRadiusMixin, PolygonMixin)

#
#   ==== BASIC CLASSES FOR GRAPHICS OBJECTS ====
#
class Text(OnePointMixin, CanvasObjectBase):
    """Draws text on a DrawingCanvas.
    Parameters are:
    x, y: 0-based coordinates in the data space
    text: the text to draw
    Optional parameters for fontsize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of lower left of text"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of lower left of text"),
            Param(name='text', type=str, default='EDIT ME',
                  description="Text to display"),
            Param(name='font', type=str, default='Sans Serif',
                  description="Font family for text"),
            Param(name='fontsize', type=int, default=None,
                  min=8, max=72,
                  description="Font size of text (default: vary by scale)"),
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
        return cls(cxt.start_x, cxt.start_y, **cxt.drawparams)

    def __init__(self, x, y, text='EDIT ME',
                 font='Sans Serif', fontsize=None,
                 color='yellow', alpha=1.0, rot_deg=0.0,
                 showcap=False, **kwdargs):
        self.kind = 'text'
        super(Text, self).__init__(color=color, alpha=alpha,
                                   x=x, y=y, font=font, fontsize=fontsize,
                                   text=text, rot_deg=rot_deg,
                                   showcap=showcap, **kwdargs)
        OnePointMixin.__init__(self)

    def select_contains(self, viewer, x, y):
        xd, yd = self.get_data_points()[0]
        return self.within_radius(viewer, x, y, xd, yd, self.cap_radius)

    def draw(self, viewer):
        cr = viewer.renderer.setup_cr(self)
        cr.set_font_from_shape(self)

        x, y = self.get_data_points()[0]
        cx, cy = self.canvascoords(viewer, x, y)
        cr.draw_text(cx, cy, self.text, rot_deg=self.rot_deg)

        if self.showcap:
            self.draw_caps(cr, self.cap, cpoints)

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
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
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
            klass = canvas.getDrawClass('line')
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

        assert len(points) > 2, \
               ValueError("Polygons need at least 3 points")

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
                  valid=['data', 'wcs'],
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

    def contains_arr_points(self, x_arr, y_arr, points, radius=1.0):
        # This code is split out of contains_arr() so that it can
        # be called from BezierCurve with a different set of points
        x1, y1 = points[0]
        contains = None
        for point in points[1:]:
            x2, y2 = point
            res = self.point_within_line(x_arr, y_arr, x1, y1, x2, y2,
                                         radius)
            if contains is None:
                contains = res
            else:
                contains = numpy.logical_or(contains, res)
            x1, y1 = x2, y2
        return contains

    def contains_arr(self, x_arr, y_arr, radius=1.0):
        return self.contains_arr_points(x_arr, y_arr, self.points,
                                        radius=radius)

    def contains(self, data_x, data_y):
        x_arr, y_arr = numpy.array([data_x]), numpy.array([data_y])
        res = self.contains_arr(x_arr, y_arr)
        return res[0]

    def select_contains_points(self, viewer, points, data_x, data_y):
        # This code is split out of contains_arr() so that it can
        # be called from BezierCurve with a different set of points
        x1, y1 = points[0]
        for point in points[1:]:
            x2, y2 = point
            if self.within_line(viewer, data_x, data_y, x1, y1, x2, y2,
                                self.cap_radius):

                return True
            x1, y1 = x2, y2
        return False

    def select_contains(self, viewer, data_x, data_y):
        points = self.get_data_points()
        return self.select_contains_points(viewer, points, data_x, data_y)

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

    TODO: need to implement contains(), which means figuring out whether a
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

    def select_contains(self, viewer, data_x, data_y):
        image = viewer.get_image()
        points = self.get_points_on_curve(image)
        return self.select_contains_points(viewer, points, data_x, data_y)

    # TODO: this probably belongs somewhere else
    def get_pixels_on_curve(self, image, getvalues=True):
        data = image.get_data()
        wd, ht = image.get_size()
        if getvalues:
            res = [ data[y, x] if 0 <= x < wd and 0 <= y < ht else numpy.NaN
                    for x, y in self.get_points_on_curve(image) ]
        else:
            res = [ [x, y] if 0 <= x < wd and 0 <= y < ht else numpy.NaN
                    for x, y in self.get_points_on_curve(image) ]
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


class Box(OnePointTwoRadiusMixin, CanvasObjectBase):
    """Draws a box on a DrawingCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    xradius, yradius: radii based on the number of pixels in data space
    Optional parameters for linesize, color, etc.
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
            Param(name='xradius', type=float, default=1.0,  argpos=2,
                  min=0.0,
                  description="X radius of object"),
            Param(name='yradius', type=float, default=1.0,  argpos=3,
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
        return cls(cxt.start_x, cxt.start_y, xradius, yradius, **cxt.drawparams)

    def __init__(self, x, y, xradius, yradius, color='red',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 rot_deg=0.0, **kwdargs):
        CanvasObjectBase.__init__(self, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  alpha=alpha, fillalpha=fillalpha,
                                  x=x, y=y, xradius=xradius,
                                  yradius=yradius, rot_deg=rot_deg,
                                  **kwdargs)
        OnePointTwoRadiusMixin.__init__(self)
        self.kind = 'box'

    def get_points(self):
        points = (self.crdmap.offset_pt((self.x, self.y),
                                        -self.xradius, -self.yradius),
                  self.crdmap.offset_pt((self.x, self.y),
                                        self.xradius, -self.yradius),
                  self.crdmap.offset_pt((self.x, self.y),
                                        self.xradius, self.yradius),
                  self.crdmap.offset_pt((self.x, self.y),
                                        -self.xradius, self.yradius),
                  )
        points = self.get_data_points(points=points)
        return points

    def contains_arr(self, x_arr, y_arr):
        points = self.get_points()
        x1, y1 = points[0]
        x2, y2 = points[2]

        # rotate points back to non-rotated cartesian alignment for test
        xd, yd = self.crdmap.to_data(self.x, self.y)
        xa, ya = trcalc.rotate_pt(x_arr, y_arr, -self.rot_deg,
                                  xoff=xd, yoff=yd)

        contains = numpy.logical_and(
            numpy.logical_and(min(x1, x2) <= xa, xa <= max(x1, x2)),
            numpy.logical_and(min(y1, y2) <= ya, ya <= max(y1, y2)))
        return contains

    def contains(self, data_x, data_y):
        x_arr, y_arr = numpy.array([data_x]), numpy.array([data_y])
        res = self.contains_arr(x_arr, y_arr)
        return res[0]

    def draw(self, viewer):
        cpoints = self.get_cpoints(viewer)

        cr = viewer.renderer.setup_cr(self)
        cr.draw_polygon(cpoints)

        if self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class SquareBox(OnePointOneRadiusMixin, CanvasObjectBase):
    """Draws a square box on a DrawingCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    radius: radius based on the number of pixels in data space
    Optional parameters for linesize, color, etc.
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
        return cls(cxt.start_x, cxt.start_y, radius, **cxt.drawparams)

    def __init__(self, x, y, radius, color='red',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 rot_deg=0.0, **kwdargs):
        CanvasObjectBase.__init__(self, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  alpha=alpha, fillalpha=fillalpha,
                                  x=x, y=y, radius=radius,
                                  rot_deg=rot_deg,
                                  **kwdargs)
        OnePointOneRadiusMixin.__init__(self)
        self.kind = 'squarebox'

    def get_points(self):
        points = (self.crdmap.offset_pt((self.x, self.y),
                                        -self.radius, -self.radius),
                  self.crdmap.offset_pt((self.x, self.y),
                                        self.radius, -self.radius),
                  self.crdmap.offset_pt((self.x, self.y),
                                        self.radius, self.radius),
                  self.crdmap.offset_pt((self.x, self.y),
                                        -self.radius, self.radius))
        points = self.get_data_points(points=points)
        return points

    def rotate_by(self, theta_deg):
        new_rot = math.fmod(self.rot_deg + theta_deg, 360.0)
        self.rot_deg = new_rot
        return new_rot

    def contains_arr(self, x_arr, y_arr):
        points = self.get_points()
        x1, y1 = points[0]
        x2, y2 = points[2]

        # rotate point back to cartesian alignment for test
        xd, yd = self.crdmap.to_data(self.x, self.y)
        xa, ya = trcalc.rotate_pt(x_arr, y_arr, -self.rot_deg,
                                  xoff=xd, yoff=yd)

        contains = numpy.logical_and(
            numpy.logical_and(min(x1, x2) <= xa, xa <= max(x1, x2)),
            numpy.logical_and(min(y1, y2) <= ya, ya <= max(y1, y2)))
        return contains

    def contains(self, data_x, data_y):
        x_arr, y_arr = numpy.array([data_x]), numpy.array([data_y])
        res = self.contains_arr(x_arr, y_arr)
        return res[0]

    def set_edit_point(self, i, pt, detail):
        if i == 0:
            self.set_point_by_index(i, pt)
        elif i == 1:
            scalef = self.calc_scale_from_pt(pt, detail)
            self.radius = detail.radius * scalef
        elif i == 2:
            delta_deg = self.calc_rotation_from_pt(pt, detail)
            self.rotate_by(delta_deg)
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self, viewer):
        points = self.get_data_points(points=(
            self.crdmap.offset_pt((self.x, self.y),
                                  self.radius, self.radius),
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


class Ellipse(OnePointTwoRadiusMixin, CanvasObjectBase):
    """Draws an ellipse on a DrawingCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    xradius, yradius: radii based on the number of pixels in data space
    Optional parameters for linesize, color, etc.
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
            Param(name='xradius', type=float, default=1.0,  argpos=2,
                  min=0.0,
                  description="X radius of object"),
            Param(name='yradius', type=float, default=1.0,  argpos=3,
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
        return cls(cxt.start_x, cxt.start_y, xradius, yradius, **cxt.drawparams)

    def __init__(self, x, y, xradius, yradius, color='yellow',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 rot_deg=0.0, **kwdargs):
        CanvasObjectBase.__init__(self, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  alpha=alpha, fillalpha=fillalpha,
                                  x=x, y=y, xradius=xradius,
                                  yradius=yradius, rot_deg=rot_deg,
                                  **kwdargs)
        OnePointTwoRadiusMixin.__init__(self)
        self.kind = 'ellipse'

    def get_points(self):
        points = ((self.x, self.y),
                  self.crdmap.offset_pt((self.x, self.y),
                                        self.xradius, 0),
                  self.crdmap.offset_pt((self.x, self.y),
                                        0, self.yradius),
                  self.crdmap.offset_pt((self.x, self.y),
                                        self.xradius, self.yradius),
                  )
        points = self.get_data_points(points=points)
        return points

    def contains_arr(self, x_arr, y_arr):
        # coerce args to floats
        x_arr = x_arr.astype(numpy.float)
        y_arr = y_arr.astype(numpy.float)

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

    def contains(self, data_x, data_y):
        x_arr, y_arr = numpy.array([data_x]), numpy.array([data_y])
        res = self.contains_arr(x_arr, y_arr)
        return res[0]

    def get_llur(self):
        # See http://stackoverflow.com/questions/87734/how-do-you-calculate-the-axis-aligned-bounding-box-of-an-ellipse
        theta = math.radians(self.rot_deg)
        sin_theta = math.sin(theta)
        cos_theta = math.cos(theta)

        # need to recalculate radius in case of wcs coords
        points = self.get_points()
        x, y = points[0]
        xradius = abs(points[1][0] - x)
        yradius = abs(points[2][1] - y)

        a = xradius * cos_theta
        b = yradius * sin_theta
        c = xradius * sin_theta
        d = yradius * cos_theta
        wd = math.sqrt(a ** 2.0 + b ** 2.0) * 2.
        ht = math.sqrt(c ** 2.0 + d ** 2.0) * 2.

        x1, y1 = x - wd * 0.5, y + ht * 0.5
        x2, y2 = x1 + wd, y1 - ht
        return self.swapxy(x1, y1, x2, y2)

    def get_bezier_pts(self):
        points = self.get_points()
        x, y = points[0]
        xradius = abs(points[1][0] - x)
        yradius = abs(points[2][1] - y)

        return bezier.get_bezier_ellipse(x, y, xradius, yradius)

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
            cp = self.get_cpoints(viewer, points=self.get_bezier_pts())
            cr.draw_ellipse_bezier(cp)

        else:
            # <- backend can draw polygons
            cp = self.get_cpoints(viewer, points=self.get_bezier_pts())
            num_pts = bezier.bezier_steps
            cp = bezier.get_bezier(num_pts, cp)
            cr.draw_polygon(cp)

        if self.showcap:
            cpoints = self.get_cpoints(viewer)
            self.draw_caps(cr, self.cap, cpoints)


class Triangle(OnePointTwoRadiusMixin, CanvasObjectBase):
    """Draws a triangle on a DrawingCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    xradius, yradius: radii based on the number of pixels in data space
    Optional parameters for linesize, color, etc.
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
            Param(name='xradius', type=float, default=1.0,  argpos=2,
                  min=0.0,
                  description="X radius of object"),
            Param(name='yradius', type=float, default=1.0,  argpos=3,
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
        return cls(cxt.start_x, cxt.start_y, xradius, yradius, **cxt.drawparams)

    def __init__(self, x, y, xradius, yradius, color='pink',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 rot_deg=0.0, **kwdargs):
        self.kind='triangle'
        CanvasObjectBase.__init__(self, color=color, alpha=alpha,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  fillalpha=fillalpha,
                                  x=x, y=y, xradius=xradius,
                                  yradius=yradius, rot_deg=rot_deg,
                                  **kwdargs)
        OnePointTwoRadiusMixin.__init__(self)

    def get_points(self):
        points = (self.crdmap.offset_pt((self.x, self.y),
                                        -2*self.xradius, -self.yradius),
                  self.crdmap.offset_pt((self.x, self.y),
                                        2*self.xradius, -self.yradius),
                  self.crdmap.offset_pt((self.x, self.y),
                                        0, self.yradius),
                  )
        points = self.get_data_points(points=points)
        return points

    def get_llur(self):
        xd, yd = self.crdmap.to_data(self.x, self.y)
        points = numpy.asarray(self.get_points())

        mpts = trcalc.rotate_coord(points, self.rot_deg, [xd, yd])
        t_ = mpts.T

        x1, y1 = t_[0].min(), t_[1].min()
        x2, y2 = t_[0].max(), t_[1].max()
        return (x1, y1, x2, y2)

    def contains_arr(self, x_arr, y_arr):
        # is this the same as self.x, self.y ?
        xd, yd = self.get_center_pt()
        # rotate point back to cartesian alignment for test
        xa, ya = trcalc.rotate_pt(x_arr, y_arr, -self.rot_deg,
                                  xoff=xd, yoff=yd)

        (x1, y1), (x2, y2), (x3, y3) = self.get_points()

        # coerce args to floats
        x_arr = x_arr.astype(numpy.float)
        y_arr = y_arr.astype(numpy.float)

        # barycentric coordinate test
        denominator = float((y2 - y3)*(x1 - x3) + (x3 - x2)*(y1 - y3))
        a = ((y2 - y3)*(xa - x3) + (x3 - x2)*(ya - y3)) / denominator
        b = ((y3 - y1)*(xa - x3) + (x1 - x3)*(ya - y3)) / denominator
        c = 1.0 - a - b

        #tf = (0.0 <= a <= 1.0 and 0.0 <= b <= 1.0 and 0.0 <= c <= 1.0)
        contains = numpy.logical_and(
            numpy.logical_and(0.0 <= a, a <= 1.0),
            numpy.logical_and(numpy.logical_and(0.0 <= b, b <= 1.0),
                              numpy.logical_and(0.0 <= c, c <= 1.0)))
        return contains

    def contains(self, data_x, data_y):
        x_arr, y_arr = numpy.array([data_x]), numpy.array([data_y])
        res = self.contains_arr(x_arr, y_arr)
        return res[0]

    def draw(self, viewer):
        cpoints = self.get_cpoints(viewer)

        cr = viewer.renderer.setup_cr(self)
        cr.draw_polygon(cpoints)

        if self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Circle(OnePointOneRadiusMixin, CanvasObjectBase):
    """Draws a circle on a DrawingCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    radius: radius based on the number of pixels in data space
    Optional parameters for linesize, color, etc.
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
        radius = math.sqrt(abs(cxt.start_x - cxt.x)**2 +
                           abs(cxt.start_y - cxt.y)**2 )
        return cls(cxt.start_x, cxt.start_y, radius, **cxt.drawparams)

    def __init__(self, x, y, radius, color='yellow',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 **kwdargs):
        CanvasObjectBase.__init__(self, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  alpha=alpha, fillalpha=fillalpha,
                                  x=x, y=y, radius=radius, **kwdargs)
        OnePointOneRadiusMixin.__init__(self)
        self.kind = 'circle'

    def contains_arr(self, x_arr, y_arr):
        xd, yd = self.crdmap.to_data(self.x, self.y)

        # need to recalculate radius in case of wcs coords
        points = self.get_data_points(points=(
            self.crdmap.offset_pt((self.x, self.y), self.radius, 0),
            self.crdmap.offset_pt((self.x, self.y), 0, self.radius),
            ))
        (x2, y2), (x3, y3) = points
        xradius = max(x2, xd) - min(x2, xd)
        yradius = max(y3, yd) - min(y3, yd)

        # need to make sure to coerce these to floats or it won't work
        x_arr = x_arr.astype(numpy.float)
        y_arr = y_arr.astype(numpy.float)

        # See http://math.stackexchange.com/questions/76457/check-if-a-point-is-within-an-ellipse
        res = (((x_arr - xd) ** 2) / xradius ** 2 +
               ((y_arr - yd) ** 2) / yradius ** 2)
        contains = (res <= 1.0)
        return contains

    def contains(self, data_x, data_y):
        x_arr, y_arr = numpy.array([data_x]), numpy.array([data_y])
        res = self.contains_arr(x_arr, y_arr)
        return res[0]

    def get_edit_points(self, viewer):
        points = self.get_data_points(points=(
            (self.x, self.y),
            self.crdmap.offset_pt((self.x, self.y), self.radius, 0),
            ))
        return [MovePoint(*points[0]),
                ScalePoint(*points[1]),
                ]

    def get_llur(self):
        points = self.get_data_points(points=(
            self.crdmap.offset_pt((self.x, self.y),
                                  -self.radius, -self.radius),
            self.crdmap.offset_pt((self.x, self.y),
                                  self.radius, self.radius),
            ))
        (x1, y1), (x2, y2) = points
        return self.swapxy(x1, y1, x2, y2)

    def draw(self, viewer):
        points = self.get_data_points(points=(
            (self.x, self.y),
            self.crdmap.offset_pt((self.x, self.y), 0, self.radius),
            ))
        cpoints = self.get_cpoints(viewer, points=points)
        cx, cy, cradius = self.calc_radius(viewer,
                                           cpoints[0], cpoints[1])
        cr = viewer.renderer.setup_cr(self)
        cr.draw_circle(cx, cy, cradius)

        if self.showcap:
            self.draw_caps(cr, self.cap, ((cx, cy), ))


class Point(OnePointOneRadiusMixin, CanvasObjectBase):
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
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of center of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of center of object"),
            Param(name='radius', type=float, default=1.0,  argpos=2,
                  min=0.0,
                  description="Radius of object"),
            Param(name='style', type=str, default='cross',
                  valid=['cross', 'plus'],
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
        return cls(cxt.start_x, cxt.start_y, radius, **cxt.drawparams)

    def __init__(self, x, y, radius, style='cross', color='yellow',
                 linewidth=1, linestyle='solid', alpha=1.0, showcap=False,
                 **kwdargs):
        self.kind = 'point'
        CanvasObjectBase.__init__(self, color=color, alpha=alpha,
                                  linewidth=linewidth,
                                  linestyle=linestyle,
                                  x=x, y=y, radius=radius,
                                  showcap=showcap, style=style,
                                  **kwdargs)
        OnePointOneRadiusMixin.__init__(self)

    def contains_arr(self, x_arr, y_arr, radius=2.0):
        xd, yd = self.crdmap.to_data(self.x, self.y)
        contains = self.point_within_radius(x_arr, y_arr, xd, yd,
                                            radius)
        return contains

    def contains(self, data_x, data_y, radius=1):
        x_arr, y_arr = numpy.array([data_x]), numpy.array([data_y])
        res = self.contains_arr(x_arr, y_arr, radius=radius)
        return res[0]

    def select_contains(self, viewer, data_x, data_y):
        xd, yd = self.crdmap.to_data(self.x, self.y)
        return self.within_radius(viewer, data_x, data_y, xd, yd,
                                  self.cap_radius)

    def get_edit_points(self, viewer):
        points = self.get_data_points(points=[(self.x, self.y)])
        move_pt, scale_pt, rotate_pt = self.get_move_scale_rotate_pts(viewer)
        return [MovePoint(*points[0]), scale_pt]

    def draw(self, viewer):
        points = self.get_data_points(points=(
            (self.x, self.y),
            self.crdmap.offset_pt((self.x, self.y), 0, self.radius),
            ))
        cpoints = self.get_cpoints(viewer, points=points)
        cx, cy, cradius = self.calc_radius(viewer,
                                           cpoints[0], cpoints[1])
        cx1, cy1 = cx - cradius, cy - cradius
        cx2, cy2 = cx + cradius, cy + cradius

        cr = viewer.renderer.setup_cr(self)

        if self.style == 'cross':
            cr.draw_line(cx1, cy1, cx2, cy2)
            cr.draw_line(cx1, cy2, cx2, cy1)
        else:
            cr.draw_line(cx1, cy, cx2, cy)
            cr.draw_line(cx, cy1, cx, cy2)

        if self.showcap:
            self.draw_caps(cr, self.cap, ((cx, cy), ))


class Rectangle(TwoPointMixin, CanvasObjectBase):
    """Draws a rectangle on a DrawingCanvas.
    Parameters are:
    x1, y1: 0-based coordinates of one corner in the data space
    x2, y2: 0-based coordinates of the opposing corner in the data space
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
        return cls(cxt.start_x, cxt.start_y, cxt.x, cxt.y, **cxt.drawparams)

    def __init__(self, x1, y1, x2, y2, color='red',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0,
                 drawdims=False, font='Sans Serif', fillalpha=1.0,
                 **kwdargs):
        self.kind = 'rectangle'

        CanvasObjectBase.__init__(self, color=color,
                                  x1=x1, y1=y1, x2=x2, y2=y2,
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

    def contains_arr(self, x_arr, y_arr):
        x1, y1, x2, y2 = self.get_llur()

        contains = numpy.logical_and(
            numpy.logical_and(x1 <= x_arr, x_arr <= x2),
            numpy.logical_and(y1 <= y_arr, y_arr <= y2))
        return contains

    def contains(self, data_x, data_y):
        x1, y1, x2, y2 = self.get_llur()

        if (x1 <= data_x <= x2) and (y1 <= data_y <= y2):
            return True
        return False

    # TO BE DEPRECATED?
    def move_point(self):
        return self.get_center_pt()

    def draw(self, viewer):
        cr = viewer.renderer.setup_cr(self)

        cpoints = self.get_cpoints(viewer)
        cr.draw_polygon(cpoints)

        if self.drawdims:
            fontsize = self.scale_font(viewer)
            cr.set_font(self.font, fontsize)

            cx1, cy1 = cpoints[0]
            cx2, cy2 = cpoints[2]

            # draw label on X dimension
            cx = cx1 + (cx2 - cx1) // 2
            cy = cy2 + -4
            cr.draw_text(cx, cy, "%f" % abs(self.x2 - self.x1))

            # draw label on Y dimension
            cy = cy1 + (cy2 - cy1) // 2
            cx = cx2 + 4
            cr.draw_text(cx, cy, "%f" % abs(self.y2 - self.y1))

        if self.showcap:
            self.draw_caps(cr, self.cap, cpoints)

class Square(Rectangle):

    @classmethod
    def idraw(cls, canvas, cxt):
        len_x = cxt.start_x - cxt.x
        len_y = cxt.start_y - cxt.y
        length = max(abs(len_x), abs(len_y))
        len_x = numpy.sign(len_x) * length
        len_y = numpy.sign(len_y) * length
        return cls(cxt.start_x, cxt.start_y,
                   cxt.start_x-len_x, cxt.start_y-len_y,
                   **cxt.drawparams)

class Line(TwoPointMixin, CanvasObjectBase):
    """Draws a line on a DrawingCanvas.
    Parameters are:
    x1, y1: 0-based coordinates of one end in the data space
    x2, y2: 0-based coordinates of the opposing end in the data space
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
        return cls(cxt.start_x, cxt.start_y, cxt.x, cxt.y, **cxt.drawparams)

    def __init__(self, x1, y1, x2, y2, color='red',
                 linewidth=1, linestyle='solid', alpha=1.0,
                 arrow=None, showcap=False, **kwdargs):
        self.kind = 'line'
        CanvasObjectBase.__init__(self, color=color, alpha=alpha,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle, arrow=arrow,
                                  x1=x1, y1=y1, x2=x2, y2=y2,
                                  **kwdargs)
        TwoPointMixin.__init__(self)

    def get_points(self):
        points = [(self.x1, self.y1), (self.x2, self.y2)]
        points = self.get_data_points(points=points)
        return points

    def contains_arr(self, x_arr, y_arr, radius=1.0):
        points = self.get_points()
        x1, y1 = points[0]
        x2, y2 = points[1]
        contains = self.point_within_line(x_arr, y_arr, x1, y1, x2, y2,
                                          radius)
        return contains

    def contains(self, data_x, data_y, radius=1.0):
        x_arr, y_arr = numpy.array([data_x]), numpy.array([data_y])
        res = self.contains_arr(x_arr, y_arr, radius=radius)
        return res[0]

    def select_contains(self, viewer, data_x, data_y):
        points = self.get_points()
        x1, y1 = points[0]
        x2, y2 = points[1]
        return self.within_line(viewer, data_x, data_y, x1, y1, x2, y2,
                                self.cap_radius)

    def draw(self, viewer):
        points = self.get_points()
        x1, y1 = points[0]
        x2, y2 = points[1]
        cx1, cy1 = self.canvascoords(viewer, x1, y1)
        cx2, cy2 = self.canvascoords(viewer, x2, y2)

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


class RightTriangle(TwoPointMixin, CanvasObjectBase):
    """Draws a right triangle on a DrawingCanvas.
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
        return cls(cxt.start_x, cxt.start_y, cxt.x, cxt.y, **cxt.drawparams)

    def __init__(self, x1, y1, x2, y2, color='pink',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 **kwdargs):
        self.kind='righttriangle'
        CanvasObjectBase.__init__(self, color=color, alpha=alpha,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  fillalpha=fillalpha,
                                  x1=x1, y1=y1, x2=x2, y2=y2,
                                  **kwdargs)
        TwoPointMixin.__init__(self)

    def get_points(self):
        points = [(self.x1, self.y1), (self.x2, self.y2),
                  (self.x2, self.y1)]
        points = self.get_data_points(points=points)
        return points

    def contains_arr(self, x_arr, y_arr):
        points = self.get_points()
        x1, y1 = points[0]
        x2, y2 = points[1]
        x3, y3 = points[2]

        # coerce args to floats
        x_arr = x_arr.astype(numpy.float)
        y_arr = y_arr.astype(numpy.float)

        # barycentric coordinate test
        denominator = float((y2 - y3)*(x1 - x3) + (x3 - x2)*(y1 - y3))
        a = ((y2 - y3)*(x_arr - x3) + (x3 - x2)*(y_arr - y3)) / denominator
        b = ((y3 - y1)*(x_arr - x3) + (x1 - x3)*(y_arr - y3)) / denominator
        c = 1.0 - a - b

        #tf = (0.0 <= a <= 1.0 and 0.0 <= b <= 1.0 and 0.0 <= c <= 1.0)
        contains = numpy.logical_and(
            numpy.logical_and(0.0 <= a, a <= 1.0),
            numpy.logical_and(numpy.logical_and(0.0 <= b, b <= 1.0),
                              numpy.logical_and(0.0 <= c, c <= 1.0)))
        return contains

    def contains(self, data_x, data_y):
        x_arr, y_arr = numpy.array([data_x]), numpy.array([data_y])
        res = self.contains_arr(x_arr, y_arr)
        return res[0]

    def draw(self, viewer):
        cpoints = self.get_cpoints(viewer)
        cr = viewer.renderer.setup_cr(self)
        cr.draw_polygon(cpoints)

        if self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


register_canvas_types(
    dict(text=Text, rectangle=Rectangle, circle=Circle,
         line=Line, point=Point, polygon=Polygon,
         freepolygon=FreePolygon, path=Path, freepath=FreePath,
         righttriangle=RightTriangle, triangle=Triangle,
         ellipse=Ellipse, square=Square, beziercurve=BezierCurve,
         box=Box, squarebox=SquareBox))

#END
