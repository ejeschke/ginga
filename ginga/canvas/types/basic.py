#
# basic.py -- classes for basic shapes drawn on ginga canvases.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import warnings
import numpy
# for BezierCurve
from collections import OrderedDict

from ginga.canvas.CanvasObject import (CanvasObjectBase, _bool, _color,
                                       register_canvas_types,
                                       colors_plus_none)
from ginga import trcalc
from ginga.misc.ParamSet import Param
from ginga.util import wcs
from ginga.util.six.moves import map

#
#   ==== MIXIN CLASSES FOR BASE OBJECTS ====
#
class TwoPointMixin(object):

    def get_center_pt(self):
        return ((self.x1 + self.x2) / 2., (self.y1 + self.y2) / 2.)

    def set_edit_point(self, i, pt):
        if i == 0:
            x, y = pt
            self.move_to(x, y)
        else:
            self.set_point_by_index(i-1, pt)

    def get_edit_points(self):
        return [self.get_center_pt(),
                (self.x1, self.y1), (self.x2, self.y2)]

    def get_llur(self):
        x1, y1 = self.crdmap.to_data(self.x1, self.y1)
        x2, y2 = self.crdmap.to_data(self.x2, self.y2)
        return self.swapxy(x1, y1, x2, y2)


class OnePointOneRadiusMixin(object):

    def get_center_pt(self):
        return (self.x, self.y)

    def get_points(self):
        return [(self.x, self.y)]

    def set_edit_point(self, i, pt):
        if i == 0:
            self.set_point_by_index(i, pt)
        elif i == 1:
            x, y = pt
            self.radius = math.sqrt(abs(x - self.x)**2 +
                                    abs(y - self.y)**2 )
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self):
        return [(self.x, self.y),
                (self.x + self.radius, self.y)]

    def rotate_by(self, theta_deg):
        pass


class OnePointTwoRadiusMixin(object):

    def get_center_pt(self):
        return (self.x, self.y)

    def set_edit_point(self, i, pt):
        if i == 0:
            self.set_point_by_index(i, pt)
        elif i == 1:
            x, y = pt
            self.xradius = abs(x - self.x)
        elif i == 2:
            x, y = pt
            self.yradius = abs(y - self.y)
        elif i == 3:
            x, y = pt
            self.xradius, self.yradius = abs(x - self.x), abs(y - self.y)
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self):
        return [(self.x, self.y),    # location
                (self.x + self.xradius, self.y),  # adj xradius
                (self.x, self.y + self.yradius),  # adj yradius
                (self.x + self.xradius, self.y + self.yradius)]   # adj both

    def rotate_by(self, theta_deg):
        new_rot = math.fmod(self.rot_deg + theta_deg, 360.0)
        self.rot_deg = new_rot
        return new_rot

    def get_llur(self):
        xd, yd = self.crdmap.to_data(self.x, self.y)
        points = ((self.x - self.xradius, self.y - self.yradius),
                  (self.x + self.xradius, self.y - self.yradius),
                  (self.x + self.xradius, self.y + self.yradius),
                  (self.x - self.xradius, self.y + self.yradius))
        mpts = numpy.array(
            list(map(lambda pt: trcalc.rotate_pt(pt[0], pt[1], self.rot_deg,
                                                 xoff=xd, yoff=yd),
                     map(lambda pt: self.crdmap.to_data(pt[0], pt[1]),
                         points))))
        t_ = mpts.T
        x1, y1 = t_[0].min(), t_[1].min()
        x2, y2 = t_[0].max(), t_[1].max()
        return (x1, y1, x2, y2)


class PolygonMixin(object):
    """Mixin for polygon-based objects.
    """

    def get_center_pt(self, closed=True):
        if closed:
            P = numpy.array(self.points + [self.points[0]])
        else:
            P = numpy.array(self.points)
        x = P[:, 0]
        y = P[:, 1]

        a = x[:-1] * y[1:]
        b = y[:-1] * x[1:]
        A = numpy.sum(a - b) / 2.

        cx = x[:-1] + x[1:]
        cy = y[:-1] + y[1:]

        Cx = numpy.sum(cx * (a - b)) / (6. * A)
        Cy = numpy.sum(cy * (a - b)) / (6. * A)
        return (Cx, Cy)

    def get_points(self):
        return self.points

    def get_llur(self):
        points = numpy.array(list(map(lambda pt: self.crdmap.to_data(pt[0], pt[1]),
                                 self.get_points())))
        t_ = points.T
        x1, y1 = t_[0].min(), t_[1].min()
        x2, y2 = t_[0].max(), t_[1].max()
        return (x1, y1, x2, y2)

    def contains_arr(self, x_arr, y_arr):
        # NOTE: we use a version of the ray casting algorithm
        # See: http://alienryderflex.com/polygon/
        xa, ya = x_arr, y_arr

        # promote input arrays dimension cardinality, if necessary
        promoted = False
        if len(xa.shape) == 1:
            xa = xa.reshape(1, -1)
            promoted = True
        if len(ya.shape) == 1:
            ya = ya.reshape(-1, 1)
            promoted = True

        result = numpy.empty((ya.size, xa.size), dtype=numpy.bool)
        result.fill(False)

        xj, yj = self.crdmap.to_data(*self.points[-1])
        for point in self.points:
            xi, yi = self.crdmap.to_data(*point)
            tf = numpy.logical_and(
                numpy.logical_or(numpy.logical_and(yi < ya, yj >= ya),
                                 numpy.logical_and(yj < ya, yi >= ya)),
                numpy.logical_or(xi <= xa, xj <= xa))
            # NOTE: get a divide by zero here for some elements whose tf=False
            # Need to figure out a way to conditionally do those w/tf=True
            # Till then we use the warnings module to suppress the warning.
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', RuntimeWarning)
                cross = ((xi + (ya - yi).astype(numpy.float) /
                          (yj - yi) * (xj - xi)) < xa)

            result[tf == True] ^= cross[tf == True]
            xj, yj = xi, yi

        if promoted:
            # de-promote result
            result = result[numpy.eye(len(y_arr), len(x_arr), dtype=numpy.bool)]
            
        return result

    def contains(self, xp, yp):
        x_arr, y_arr = numpy.array([xp]), numpy.array([yp])
        res = self.contains_arr(x_arr, y_arr)
        return res[0]

    def set_edit_point(self, i, pt):
        if i == 0:
            x, y = pt
            self.move_to(x, y)
        elif i-1 < len(self.points):
            self.set_point_by_index(i-1, pt)
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self):
        return [self.get_center_pt()] + self.points


#
#   ==== BASIC CLASSES FOR GRAPHICS OBJECTS ====
#
class Text(CanvasObjectBase):
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

    def get_center_pt(self):
        return (self.x, self.y)

    def select_contains(self, viewer, x, y):
        return self.within_radius(viewer, x, y, self.x, self.y,
                                  self.cap_radius)

    def get_points(self):
        return [self.get_center_pt()]

    def set_edit_point(self, i, pt):
        if i == 0:
            self.set_point_by_index(i, pt)
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self):
        # TODO: edit point for scaling or rotating?
        return [(self.x, self.y)]

    def draw(self, viewer):
        cr = viewer.renderer.setup_cr(self)
        cr.set_font_from_shape(self)

        cx, cy = self.canvascoords(viewer, self.x, self.y)
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
        points.append((cxt.x, cxt.y))
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
        x1, y1 = self.crdmap.to_data(*points[0])
        contains = None
        for point in points[1:]:
            x2, y2 = self.crdmap.to_data(*point)
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
        points = list(map(lambda pt: self.crdmap.to_data(pt[0], pt[1]),
                          self.points))
        return self.select_contains_points(viewer, points,
                                           data_x, data_y)

    def get_center_pt(self):
        # default is geometric average of points
        P = numpy.array(self.get_points())
        x = P[:, 0]
        y = P[:, 1]
        Cx = numpy.sum(x) / float(len(x))
        Cy = numpy.sum(y) / float(len(y))
        return (Cx, Cy)

    def draw(self, viewer):
        cpoints = self.get_cpoints(viewer, points=self.points)

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

    def calc_bezier_curve_range(self, steps, points):
        """Hacky method to get an ordered set of points that are on the
        Bezier curve.  This is used by some backends (which don't support
        drawing cubic Bezier curves) to render the curve using paths.
        """
        n = len(points) - 1
        fact_n = math.factorial(n)

        # press OrderedDict into use as an OrderedSet of points
        d = OrderedDict()

        m = float(steps - 1)

        # TODO: optomize this code as much as possible
        for i in range(steps):
            #t = i / float(steps - 1)
            t = i / m

            # optomize a call to calculate the bezier point
            #x, y = bezier(t, points)
            x = y = 0
            for j, pos in enumerate(points):
                #bern = bernstein(t, j, n)
                bin = fact_n / float(math.factorial(j) * math.factorial(n - j))
                bern = bin * (t ** j) * ((1 - t) ** (n - j))
                x += pos[0] * bern
                y += pos[1] * bern

            # convert to integer data coordinates and remove duplicates
            d[int(round(x)), int(round(y))] = None

        return list(d.keys())

    def get_points_on_curve(self, image):
        points = list(map(lambda pt: self.crdmap.to_data(pt[0], pt[1]),
                                      self.points))
        # use maximum dimension of image to estimate a reasonable number
        # of intermediate points
        steps = max(*image.get_size())
        return self.calc_bezier_curve_range(steps, points)

    def select_contains(self, viewer, data_x, data_y):
        image = viewer.get_image()
        points = self.get_points_on_curve(image)
        return self.select_contains_points(viewer, points, data_x, data_y)

    # TODO: this probably belongs somewhere else
    def get_pixels_on_curve(self, image):
        data = image.get_data()
        wd, ht = image.get_size()
        res = [ data[y, x] if 0 <= x < wd and 0 <= y < ht else numpy.NaN
                for x, y in self.get_points_on_curve(image) ]
        return res

    def draw(self, viewer):
        cpoints = self.get_cpoints(viewer, points=self.points)

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
                steps = max(*viewer.get_window_size())
                ipoints = self.calc_bezier_curve_range(steps, cpoints)
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
        points = ((self.x - self.xradius, self.y - self.yradius),
                  (self.x + self.xradius, self.y - self.yradius),
                  (self.x + self.xradius, self.y + self.yradius),
                  (self.x - self.xradius, self.y + self.yradius))
        return points

    def contains_arr(self, x_arr, y_arr):
        x1, y1 = self.crdmap.to_data(self.x - self.xradius,
                                     self.y - self.yradius)
        x2, y2 = self.crdmap.to_data(self.x + self.xradius,
                                     self.y + self.yradius)

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
        points = ((self.x - self.radius, self.y - self.radius),
                  (self.x + self.radius, self.y - self.radius),
                  (self.x + self.radius, self.y + self.radius),
                  (self.x - self.radius, self.y + self.radius))
        return points

    def rotate_by(self, theta_deg):
        new_rot = math.fmod(self.rot_deg + theta_deg, 360.0)
        self.rot_deg = new_rot
        return new_rot

    def get_llur(self):
        xd, yd = self.crdmap.to_data(self.x, self.y)
        points = ((self.x - self.radius, self.y - self.radius),
                  (self.x + self.radius, self.y - self.radius),
                  (self.x + self.radius, self.y + self.radius),
                  (self.x - self.radius, self.y + self.radius))
        mpts = numpy.array(
            list(map(lambda pt: trcalc.rotate_pt(pt[0], pt[1], self.rot_deg,
                                                 xoff=xd, yoff=yd),
                     map(lambda pt: self.crdmap.to_data(pt[0], pt[1]),
                         points))))
        t_ = mpts.T
        x1, y1 = t_[0].min(), t_[1].min()
        x2, y2 = t_[0].max(), t_[1].max()
        return (x1, y1, x2, y2)

    def contains_arr(self, x_arr, y_arr):
        x1, y1 = self.crdmap.to_data(self.x - self.radius,
                                     self.y - self.radius)
        x2, y2 = self.crdmap.to_data(self.x + self.radius,
                                     self.y + self.radius)

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

    def set_edit_point(self, i, pt):
        if i == 0:
            self.set_point_by_index(i, pt)
        elif i == 1:
            x, y = pt
            self.radius = max(abs(x - self.x), abs(y - self.y))
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self):
        return [(self.x, self.y),
                (self.x + self.radius, self.y + self.radius)]

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
        return [self.get_center_pt()]

    def contains_arr(self, x_arr, y_arr):
        # coerce args to floats
        x_arr = x_arr.astype(numpy.float)
        y_arr = y_arr.astype(numpy.float)

        # rotate point back to cartesian alignment for test
        xd, yd = self.crdmap.to_data(self.x, self.y)
        xa, ya = trcalc.rotate_pt(x_arr, y_arr, -self.rot_deg,
                                  xoff=xd, yoff=yd)

        # need to recalculate radius in case of wcs coords
        x2, y2 = self.crdmap.to_data(self.x + self.xradius,
                                     self.y + self.yradius)
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

    def get_bezier_pts(self, kappa=0.5522848):
        """Used by drawing subclasses to draw the ellipse."""

        mx, my = self.x, self.y
        xs, ys = mx - self.xradius, my - self.yradius
        ox, oy = self.xradius * kappa, self.yradius * kappa
        xe, ye = mx + self.xradius, my + self.yradius

        pts = [(xs, my),
               (xs, my - oy), (mx - ox, ys), (mx, ys),
               (mx + ox, ys), (xe, my - oy), (xe, my),
               (xe, my + oy), (mx + ox, ye), (mx, ye),
               (mx - ox, ye), (xs, my + oy), (xs, my)]
        return pts

    def draw(self, viewer):
        cr = viewer.renderer.setup_cr(self)

        if hasattr(cr, 'draw_ellipse_bezier'):
            cp = self.get_cpoints(viewer, points=self.get_bezier_pts())
            cr.draw_ellipse_bezier(cp)
        else:
            cpoints = self.get_cpoints(viewer, points=self.get_edit_points())
            cx, cy = cpoints[0]
            cxradius = abs(cpoints[1][0] - cx)
            cyradius = abs(cpoints[2][1] - cy)
            cr.draw_ellipse(cx, cy, cxradius, cyradius, self.rot_deg)

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
        return [(self.x - 2*self.xradius, self.y - self.yradius),
                (self.x + 2*self.xradius, self.y - self.yradius),
                (self.x, self.y + self.yradius)]


    def get_llur(self):
        xd, yd = self.crdmap.to_data(self.x, self.y)
        points = ((self.x - self.xradius*2, self.y - self.yradius),
                  (self.x + self.xradius*2, self.y - self.yradius),
                  (self.x + self.xradius*2, self.y + self.yradius),
                  (self.x - self.xradius*2, self.y + self.yradius))
        mpts = numpy.array(
            list(map(lambda pt: trcalc.rotate_pt(pt[0], pt[1], self.rot_deg,
                                                 xoff=xd, yoff=yd),
                     map(lambda pt: self.crdmap.to_data(pt[0], pt[1]),
                         points))))
        t_ = mpts.T
        x1, y1 = t_[0].min(), t_[1].min()
        x2, y2 = t_[0].max(), t_[1].max()
        return (x1, y1, x2, y2)

    def contains_arr(self, x_arr, y_arr):
        # is this the same as self.x, self.y ?
        ctr_x, ctr_y = self.get_center_pt()
        xd, yd = self.crdmap.to_data(ctr_x, ctr_y)
        # rotate point back to cartesian alignment for test
        xa, ya = trcalc.rotate_pt(x_arr, y_arr, -self.rot_deg,
                                  xoff=xd, yoff=yd)

        (x1, y1), (x2, y2), (x3, y3) = self.get_points()
        x1, y1 = self.crdmap.to_data(x1, y1)
        x2, y2 = self.crdmap.to_data(x2, y2)
        x3, y3 = self.crdmap.to_data(x3, y3)

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
        x2, y2 = self.crdmap.to_data(self.x + self.radius, self.y)
        x3, y3 = self.crdmap.to_data(self.x, self.y + self.radius)
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

    def get_llur(self):
        x1, y1 = self.crdmap.to_data(self.x - self.radius,
                                     self.y - self.radius)
        x2, y2 = self.crdmap.to_data(self.x + self.radius,
                                     self.y + self.radius)
        return self.swapxy(x1, y1, x2, y2)

    def draw(self, viewer):
        cx, cy, cradius = self.calc_radius(viewer, self.x, self.y,
                                           self.radius)
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

    def get_llur(self):
        x, y = self.crdmap.to_data(self.x, self.y)
        return (x-0.5, y-0.5, x+0.5, y+0.5)

    def get_edit_points(self):
        return [(self.x, self.y),
                # TODO: account for point style
                (self.x + self.radius, self.y + self.radius)]

    def draw(self, viewer):
        cx, cy, cradius = self.calc_radius(viewer, self.x, self.y,
                                           self.radius)
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

        cpoints = self.get_cpoints(viewer,
                                   points=((self.x1, self.y1),
                                           (self.x2, self.y1),
                                           (self.x2, self.y2),
                                           (self.x1, self.y2)))
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
        len_x = cmp(len_x, 0) * length
        len_y = cmp(len_y, 0) * length
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
        return [(self.x1, self.y1), (self.x2, self.y2)]

    def contains_arr(self, x_arr, y_arr, radius=1.0):
        x1, y1 = self.crdmap.to_data(self.x1, self.y1)
        x2, y2 = self.crdmap.to_data(self.x2, self.y2)
        contains = self.point_within_line(x_arr, y_arr, x1, y1, x2, y2,
                                          radius)
        return contains

    def contains(self, data_x, data_y, radius=1.0):
        x_arr, y_arr = numpy.array([data_x]), numpy.array([data_y])
        res = self.contains_arr(x_arr, y_arr, radius=radius)
        return res[0]

    def select_contains(self, viewer, data_x, data_y):
        x1, y1 = self.crdmap.to_data(self.x1, self.y1)
        x2, y2 = self.crdmap.to_data(self.x2, self.y2)
        return self.within_line(viewer, data_x, data_y, x1, y1, x2, y2,
                                self.cap_radius)

    def draw(self, viewer):
        cx1, cy1 = self.canvascoords(viewer, self.x1, self.y1)
        cx2, cy2 = self.canvascoords(viewer, self.x2, self.y2)

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
        return [(self.x1, self.y1), (self.x2, self.y2)]

    def contains_arr(self, x_arr, y_arr):

        x1, y1, x2, y2 = self.x1, self.y1, self.x2, self.y2
        x3, y3 = self.x2, self.y1
        x1, y1 = self.crdmap.to_data(x1, y1)
        x2, y2 = self.crdmap.to_data(x2, y2)
        x3, y3 = self.crdmap.to_data(x3, y3)

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
        ## x1, y1, x2, y2 = self.x1, self.y1, self.x2, self.y2
        ## x3, y3 = self.x2, self.y1

        ## x1, y1 = self.crdmap.to_data(x1, y1)
        ## x2, y2 = self.crdmap.to_data(x2, y2)
        ## x3, y3 = self.crdmap.to_data(x3, y3)

        ## barycentric coordinate test
        ## denominator = ((y2 - y3)*(x1 - x3) + (x3 - x2)*(y1 - y3))
        ## a = ((y2 - y3)*(data_x - x3) + (x3 - x2)*(data_y - y3)) / denominator
        ## b = ((y3 - y1)*(data_x - x3) + (x1 - x3)*(data_y - y3)) / denominator
        ## c = 1.0 - a - b

        ## tf = (0.0 <= a <= 1.0 and 0.0 <= b <= 1.0 and 0.0 <= c <= 1.0)
        ## return tf

    def draw(self, viewer):
        cpoints = self.get_cpoints(viewer,
                                   points=((self.x1, self.y1),
                                           (self.x2, self.y2),
                                           (self.x2, self.y1)))
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
